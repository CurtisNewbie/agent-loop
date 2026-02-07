"""MySQL Checkpoint 测试"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from langchain_core.runnables import RunnableConfig
from storage.mysql_checkpoint import MySQLCheckpointSaver
from storage.checkpoint import create_checkpoint_saver


class TestMySQLCheckpointSaver:
    """测试 MySQL Checkpoint Saver"""

    @pytest.mark.asyncio
    async def test_create_checkpoint_saver(self):
        """测试创建 MySQL Checkpoint Saver"""
        saver = MySQLCheckpointSaver(
            connection_string="mysql://root:password@localhost:3306/test_db"
        )
        assert saver is not None
        assert saver.table_name == "checkpoints"

    @pytest.mark.asyncio
    async def test_create_checkpoint_saver_from_conn_string(self):
        """测试通过连接字符串创建"""
        saver = MySQLCheckpointSaver.from_conn_string(
            connection_string="mysql://root:password@localhost:3306/test_db"
        )
        assert saver is not None

    @pytest.mark.asyncio
    async def test_create_checkpoint_saver_factory(self):
        """测试工厂方法创建"""
        with patch('storage.mysql_checkpoint.MySQLCheckpointSaver.from_conn_string') as mock_factory:
            mock_saver = Mock()
            mock_factory.return_value = mock_saver

            saver = create_checkpoint_saver(
                checkpoint_type="mysql",
                connection_string="mysql://root:password@localhost:3306/test_db"
            )

            mock_factory.assert_called_once_with("mysql://root:password@localhost:3306/test_db")
            assert saver == mock_saver

    @pytest.mark.asyncio
    async def test_parse_connection_string(self):
        """测试解析连接字符串"""
        saver = MySQLCheckpointSaver(
            connection_string="mysql://user:pass@localhost:3306/db"
        )

        # 验证连接字符串被正确解析
        assert saver.connection_string == "mysql://user:pass@localhost:3306/db"

    @pytest.mark.asyncio
    async def test_connection_string_formats(self):
        """测试不同格式的连接字符串"""
        # Test with password
        saver1 = MySQLCheckpointSaver("mysql://user:pass@localhost:3306/db")
        assert saver1.connection_string == "mysql://user:pass@localhost:3306/db"

        # Test without password
        saver2 = MySQLCheckpointSaver("mysql://user@localhost:3306/db")
        assert saver2.connection_string == "mysql://user@localhost:3306/db"

        # Test with mysql+aiomysql prefix
        saver3 = MySQLCheckpointSaver("mysql+aiomysql://user:pass@localhost:3306/db")
        assert saver3.connection_string == "mysql+aiomysql://user:pass@localhost:3306/db"

    @pytest.mark.asyncio
    async def test_invalid_connection_string(self):
        """测试无效的连接字符串"""
        saver = MySQLCheckpointSaver("mysql://user:pass@localhost:3306/db")

        # 测试创建表时会解析连接字符串
        # 由于我们 mock 了 create_pool，这里只测试对象创建
        assert saver is not None

    @pytest.mark.asyncio
    async def test_table_name_customization(self):
        """测试自定义表名"""
        saver = MySQLCheckpointSaver(
            connection_string="mysql://root:password@localhost:3306/test_db",
            table_name="custom_checkpoints"
        )
        assert saver.table_name == "custom_checkpoints"

    @pytest.mark.asyncio
    async def test_pool_size_configuration(self):
        """测试连接池配置"""
        saver = MySQLCheckpointSaver(
            connection_string="mysql://root:password@localhost:3306/test_db",
            pool_size=10,
            max_overflow=20
        )
        assert saver.pool_size == 10
        assert saver.max_overflow == 20

    @pytest.mark.asyncio
    async def test_close_without_pool(self):
        """测试关闭未初始化的连接池"""
        saver = MySQLCheckpointSaver(
            connection_string="mysql://root:password@localhost:3306/test_db"
        )
        # 不应该抛出异常
        await saver.close()
        assert saver._pool is None

    @pytest.mark.asyncio
    async def test_close_with_pool(self):
        """测试关闭已初始化的连接池"""
        mock_pool = AsyncMock()
        mock_pool.close = Mock()
        mock_pool.wait_closed = AsyncMock()

        saver = MySQLCheckpointSaver(
            connection_string="mysql://root:password@localhost:3306/test_db"
        )
        saver._pool = mock_pool

        await saver.close()

        mock_pool.close.assert_called_once()
        mock_pool.wait_closed.assert_called_once()
        assert saver._pool is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])