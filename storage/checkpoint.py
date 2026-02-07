"""Checkpoint 存储实现"""
from typing import Optional
from langgraph.checkpoint.memory import MemorySaver
from storage.mysql_checkpoint import MySQLCheckpointSaver


def create_checkpoint_saver(checkpoint_type: str = "memory", **kwargs) -> Optional[object]:
    """
    创建 Checkpoint Saver

    Args:
        checkpoint_type: checkpoint 类型 ("memory", "postgres", "mysql", "redis")
        **kwargs: 额外参数（如 connection_string）

    Returns:
        Checkpoint Saver 实例
    """
    if checkpoint_type == "memory":
        return MemorySaver()
    elif checkpoint_type == "postgres":
        # Note: PostgreSQL support requires langgraph-checkpoint-postgres package
        from langgraph.checkpoint.postgres import PostgresCheckpointSaver
        return PostgresCheckpointSaver.from_conn_string(kwargs.get("connection_string"))
    elif checkpoint_type == "mysql":
        return MySQLCheckpointSaver.from_conn_string(kwargs.get("connection_string"))
    elif checkpoint_type == "redis":
        # Note: Redis support requires langgraph-checkpoint-redis package
        from langgraph.checkpoint.redis import RedisCheckpointSaver
        return RedisCheckpointSaver.from_conn_string(kwargs.get("connection_string"))
    else:
        raise ValueError(f"Unknown checkpoint type: {checkpoint_type}")