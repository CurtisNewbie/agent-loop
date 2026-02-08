"""Memory Compaction for Agent Loop - Trim messages to fit context window"""
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.language_models import BaseChatModel


class CompactionStrategy(str, Enum):
    """Memory compaction strategies"""
    SLIDING_WINDOW = "sliding_window"  # Keep last N messages
    TOKEN_AWARE = "token_aware"  # Trim based on token count
    SUMMARY = "summary"  # Summarize old messages
    HYBRID = "hybrid"  # Combine strategies


class MemoryCompactor:
    """Memory compaction utility for trimming messages to fit context window"""

    def __init__(
        self,
        llm: BaseChatModel,
        strategy: CompactionStrategy = CompactionStrategy.TOKEN_AWARE,
        max_tokens: Optional[int] = None,
        max_messages: Optional[int] = None,
        keep_system_message: bool = True,
        keep_last_n_messages: int = 10,
    ):
        """
        Initialize memory compactor

        Args:
            llm: Language model instance (for token counting and summarization)
            strategy: Compaction strategy to use
            max_tokens: Maximum tokens to keep (None = use model's context window)
            max_messages: Maximum number of messages to keep (for sliding window)
            keep_system_message: Whether to always keep system messages
            keep_last_n_messages: Minimum number of recent messages to keep
        """
        self.llm = llm
        self.strategy = strategy
        self.max_tokens = max_tokens
        self.max_messages = max_messages
        self.keep_system_message = keep_system_message
        self.keep_last_n_messages = keep_last_n_messages

        # Estimate model context window if not provided
        if self.max_tokens is None:
            self.max_tokens = self._estimate_context_window()

    def _estimate_context_window(self) -> int:
        """Estimate model context window size"""
        model_name = getattr(self.llm, 'model_name', '') or getattr(self.llm, 'model', '')
        model_name = str(model_name).lower()

        # Common model context windows (order matters - check specific models first)
        context_windows = [
            ('gpt-4o', 128000),
            ('gpt-4-turbo', 128000),
            ('gpt-4', 8192),
            ('claude-3-5-sonnet', 200000),
            ('claude-3-opus', 200000),
            ('claude-3-haiku', 200000),
            ('gpt-3.5-turbo', 16385),
        ]

        for key, window in context_windows:
            if key in model_name:
                return window

        # Default conservative estimate
        return 8000

    def count_tokens(self, messages: List[BaseMessage]) -> int:
        """
        Count total tokens in messages

        Note: This is an approximation. For accurate counting, use tiktoken or similar.
        """
        total = 0
        for msg in messages:
            # Rough estimate: 1 token ≈ 4 characters
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            total += len(content) // 4

            # Add overhead for tool calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                total += len(msg.tool_calls) * 50

        return total

    def trim_messages(
        self,
        messages: List[BaseMessage],
        current_tokens: Optional[int] = None,
    ) -> List[BaseMessage]:
        """
        Trim messages according to configured strategy

        Args:
            messages: List of messages to trim
            current_tokens: Current token count (None = will be calculated)

        Returns:
            Trimmed list of messages
        """
        if not messages:
            return messages

        if current_tokens is None:
            current_tokens = self.count_tokens(messages)

        # If within limits, no trimming needed
        if current_tokens <= self.max_tokens:
            return messages

        # Apply strategy
        if self.strategy == CompactionStrategy.SLIDING_WINDOW:
            return self._trim_sliding_window(messages)
        elif self.strategy == CompactionStrategy.TOKEN_AWARE:
            return self._trim_token_aware(messages)
        elif self.strategy == CompactionStrategy.SUMMARY:
            return self._trim_with_summary(messages)
        elif self.strategy == CompactionStrategy.HYBRID:
            return self._trim_hybrid(messages)
        else:
            return self._trim_token_aware(messages)

    def _trim_sliding_window(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Trim using sliding window strategy"""
        max_msgs = self.max_messages or self.keep_last_n_messages

        # Separate system messages
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        other_messages = [m for m in messages if not isinstance(m, SystemMessage)]

        # Keep system messages if configured
        if self.keep_system_message:
            result = system_messages
        else:
            result = []

        # Keep last N messages
        result.extend(other_messages[-max_msgs:])

        return result

    def _trim_token_aware(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Trim based on token count"""
        # Separate system messages
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        other_messages = [m for m in messages if not isinstance(m, SystemMessage)]

        # Keep system messages if configured
        if self.keep_system_message:
            result = system_messages.copy()
            system_tokens = self.count_tokens(system_messages)
        else:
            result = []
            system_tokens = 0

        # Reserve space for recent messages
        recent_messages = other_messages[-self.keep_last_n_messages:]
        recent_tokens = self.count_tokens(recent_messages)

        # Calculate available tokens for middle messages
        available_tokens = self.max_tokens - system_tokens - recent_tokens

        # Add middle messages until we hit the limit
        middle_messages = other_messages[:-self.keep_last_n_messages]
        current_tokens = system_tokens

        for msg in reversed(middle_messages):
            msg_tokens = self.count_tokens([msg])
            if current_tokens + msg_tokens <= available_tokens:
                result.insert(0, msg)
                current_tokens += msg_tokens
            else:
                break

        # Add recent messages
        result.extend(recent_messages)

        return result

    async def _trim_with_summary(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Trim by summarizing old messages"""
        if len(messages) <= self.keep_last_n_messages:
            return messages

        # Separate system messages
        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        old_messages = messages[:-self.keep_last_n_messages]
        recent_messages = messages[-self.keep_last_n_messages:]

        # Keep system messages
        result = system_messages.copy() if self.keep_system_message else []

        # Summarize old messages (excluding system messages)
        messages_to_summarize = [m for m in old_messages if not isinstance(m, SystemMessage)]

        if messages_to_summarize:
            summary = await self._create_summary(messages_to_summarize)
            if summary:
                result.append(summary)

        # Add recent messages
        result.extend(recent_messages)

        return result

    async def _create_summary(self, messages: List[BaseMessage]) -> Optional[SystemMessage]:
        """Create a summary of messages"""
        from langchain_core.prompts import ChatPromptTemplate

        # Build conversation text
        conversation = []
        for msg in messages:
            role = msg.__class__.__name__
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            conversation.append(f"{role}: {content}")

        conversation_text = "\n\n".join(conversation)

        # Create summary prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Summarize the following conversation in a concise manner, preserving key information and context."),
            ("human", "{conversation}")
        ])

        try:
            response = await (prompt | self.llm).ainvoke({"conversation": conversation_text})
            summary_text = response.content if isinstance(response.content, str) else str(response.content)
            return SystemMessage(content=f"[Summary of previous conversation]: {summary_text}")
        except Exception:
            # If summarization fails, return None (no summary)
            return None

    def _trim_hybrid(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Hybrid strategy: combine sliding window with token awareness"""
        # First apply sliding window to reduce size
        trimmed = self._trim_sliding_window(messages)

        # Then apply token-aware trimming if still over limit
        current_tokens = self.count_tokens(trimmed)
        if current_tokens > self.max_tokens:
            trimmed = self._trim_token_aware(trimmed)

        return trimmed

    def get_compaction_info(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """
        Get information about message state for monitoring

        Returns:
            Dictionary with compaction statistics
        """
        total_tokens = self.count_tokens(messages)
        message_count = len(messages)
        system_count = sum(1 for m in messages if isinstance(m, SystemMessage))
        human_count = sum(1 for m in messages if isinstance(m, HumanMessage))
        ai_count = sum(1 for m in messages if isinstance(m, AIMessage))
        tool_count = sum(1 for m in messages if isinstance(m, ToolMessage))

        return {
            "total_messages": message_count,
            "total_tokens": total_tokens,
            "max_tokens": self.max_tokens,
            "token_usage_ratio": total_tokens / self.max_tokens if self.max_tokens > 0 else 0,
            "needs_compaction": total_tokens > self.max_tokens,
            "message_breakdown": {
                "system": system_count,
                "human": human_count,
                "ai": ai_count,
                "tool": tool_count,
            },
            "strategy": self.strategy.value,
        }


def create_memory_compactor(
    llm: BaseChatModel,
    strategy: str = "token_aware",
    max_tokens: Optional[int] = None,
    max_messages: Optional[int] = None,
    keep_system_message: bool = True,
    keep_last_n_messages: int = 10,
) -> MemoryCompactor:
    """
    Factory function to create a MemoryCompactor

    Args:
        llm: Language model instance
        strategy: Compaction strategy ("sliding_window", "token_aware", "summary", "hybrid")
        max_tokens: Maximum tokens to keep
        max_messages: Maximum number of messages (for sliding window)
        keep_system_message: Whether to keep system messages
        keep_last_n_messages: Minimum number of recent messages to keep

    Returns:
        MemoryCompactor instance
    """
    return MemoryCompactor(
        llm=llm,
        strategy=CompactionStrategy(strategy),
        max_tokens=max_tokens,
        max_messages=max_messages,
        keep_system_message=keep_system_message,
        keep_last_n_messages=keep_last_n_messages,
    )