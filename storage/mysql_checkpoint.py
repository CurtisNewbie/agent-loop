"""MySQL Checkpoint Saver implementation"""
import json
from typing import Optional, Dict, Any, AsyncIterator, Tuple, Sequence
from datetime import datetime
import asyncio

import aiomysql
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


class MySQLCheckpointSaver(BaseCheckpointSaver):
    """MySQL-based checkpoint saver for LangGraph"""

    def __init__(
        self,
        connection_string: str,
        table_name: str = "checkpoints",
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        """
        Initialize MySQL checkpoint saver.

        Args:
            connection_string: MySQL connection string (e.g., "mysql://user:pass@host:port/db")
            table_name: Name of the checkpoint table
            pool_size: Connection pool size
            max_overflow: Maximum overflow for connection pool
        """
        super().__init__(serde=JsonPlusSerializer())
        self.connection_string = connection_string
        self.table_name = table_name
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._pool: Optional[aiomysql.Pool] = None
        self._lock = asyncio.Lock()

    async def _get_pool(self) -> aiomysql.Pool:
        """Get or create connection pool"""
        if self._pool is None:
            async with self._lock:
                if self._pool is None:
                    # Parse connection string
                    # Format: mysql://user:password@host:port/database
                    if self.connection_string.startswith("mysql://"):
                        conn_str = self.connection_string[8:]
                    elif self.connection_string.startswith("mysql+aiomysql://"):
                        conn_str = self.connection_string[18:]
                    else:
                        raise ValueError(
                            "Invalid connection string format. "
                            "Expected: mysql://user:password@host:port/database"
                        )

                    # Parse connection string
                    if "@" in conn_str:
                        credentials, rest = conn_str.split("@", 1)
                        user, password = credentials.split(":", 1) if ":" in credentials else (credentials, "")
                    else:
                        user = "root"
                        password = ""
                        rest = conn_str

                    if "/" in rest:
                        host_port, database = rest.rsplit("/", 1)
                    else:
                        host_port = rest
                        database = "langgraph"

                    if ":" in host_port:
                        host, port_str = host_port.split(":", 1)
                        port = int(port_str)
                    else:
                        host = host_port
                        port = 3306

                    self._pool = await aiomysql.create_pool(
                        host=host,
                        port=port,
                        user=user,
                        password=password,
                        db=database,
                        minsize=1,
                        maxsize=self.pool_size + self.max_overflow,
                        autocommit=True,
                    )

                    # Create table if not exists
                    await self._create_table()

        return self._pool

    async def _create_table(self):
        """Create checkpoints table if not exists"""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        thread_id VARCHAR(255) NOT NULL,
                        checkpoint_ns VARCHAR(255) NOT NULL,
                        checkpoint_id VARCHAR(255) NOT NULL,
                        parent_checkpoint_id VARCHAR(255),
                        checkpoint JSON NOT NULL,
                        metadata JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
                await cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_thread_id
                    ON {self.table_name} (thread_id);
                """)
                await cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_checkpoint_ns
                    ON {self.table_name} (checkpoint_ns);
                """)

    async def aget_tuple(
        self,
        config: RunnableConfig,
    ) -> Optional[Tuple[Optional[Checkpoint], RunnableConfig, Optional[CheckpointMetadata]]]:
        """Get checkpoint tuple from MySQL"""
        pool = await self._get_pool()
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id")

        if not thread_id:
            return None

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if checkpoint_id:
                    await cursor.execute(
                        f"""
                        SELECT checkpoint, metadata
                        FROM {self.table_name}
                        WHERE thread_id = %s AND checkpoint_ns = %s AND checkpoint_id = %s
                        """,
                        (thread_id, checkpoint_ns, checkpoint_id)
                    )
                else:
                    # Get latest checkpoint
                    await cursor.execute(
                        f"""
                        SELECT checkpoint, metadata
                        FROM {self.table_name}
                        WHERE thread_id = %s AND checkpoint_ns = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        (thread_id, checkpoint_ns)
                    )

                row = await cursor.fetchone()
                if row:
                    checkpoint_dict = json.loads(row["checkpoint"])
                    checkpoint = self.serde.loads(checkpoint_dict)

                    metadata_dict = json.loads(row["metadata"]) if row["metadata"] else {}
                    metadata = CheckpointMetadata(**metadata_dict) if metadata_dict else None

                    return checkpoint, config, metadata

        return None

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: Optional[CheckpointMetadata] = None,
    ) -> RunnableConfig:
        """Save checkpoint to MySQL"""
        pool = await self._get_pool()
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")

        if not thread_id:
            raise ValueError("thread_id is required in config")

        checkpoint_id = checkpoint.get("id", "")
        parent_checkpoint_id = checkpoint.get("parent_checkpoint_id")

        # Serialize checkpoint
        checkpoint_dict = self.serde.dumps(checkpoint)
        checkpoint_json = json.dumps(checkpoint_dict)

        # Serialize metadata
        metadata_json = json.dumps(metadata) if metadata else None

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""
                    INSERT INTO {self.table_name}
                    (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, checkpoint, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    checkpoint = VALUES(checkpoint),
                    metadata = VALUES(metadata)
                    """,
                    (thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, checkpoint_json, metadata_json)
                )

        return config

    async def alist(
        self,
        config: RunnableConfig,
        *,
        limit: int = 10,
        before: Optional[RunnableConfig] = None,
    ) -> AsyncIterator[Tuple[RunnableConfig, Checkpoint, CheckpointMetadata]]:
        """List checkpoints from MySQL"""
        pool = await self._get_pool()
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")

        if not thread_id:
            return

        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(
                    f"""
                    SELECT checkpoint_id, checkpoint, metadata
                    FROM {self.table_name}
                    WHERE thread_id = %s AND checkpoint_ns = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (thread_id, checkpoint_ns, limit)
                )

                rows = await cursor.fetchall()
                for row in rows:
                    checkpoint_dict = json.loads(row["checkpoint"])
                    checkpoint = self.serde.loads(checkpoint_dict)

                    metadata_dict = json.loads(row["metadata"]) if row["metadata"] else {}
                    metadata = CheckpointMetadata(**metadata_dict) if metadata_dict else None

                    config_copy = RunnableConfig(
                        configurable={
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": row["checkpoint_id"]
                        }
                    )

                    yield config_copy, checkpoint, metadata

    async def adelete(self, config: RunnableConfig) -> None:
        """Delete checkpoint from MySQL"""
        pool = await self._get_pool()
        thread_id = config.get("configurable", {}).get("thread_id")
        checkpoint_ns = config.get("configurable", {}).get("checkpoint_ns", "")

        if not thread_id:
            return

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""
                    DELETE FROM {self.table_name}
                    WHERE thread_id = %s AND checkpoint_ns = %s
                    """,
                    (thread_id, checkpoint_ns)
                )

    async def close(self) -> None:
        """Close connection pool"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    @classmethod
    def from_conn_string(
        cls,
        connection_string: str,
        table_name: str = "checkpoints",
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> "MySQLCheckpointSaver":
        """Create MySQLCheckpointSaver from connection string"""
        return cls(connection_string, table_name, pool_size, max_overflow)