import logging

import redis

logger = logging.getLogger(__name__)


class RedisConnection:
    def __init__(self,host: str ="localhost",port: int = 6379, db: int = 0, password:str|None=None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.client: redis.Redis | None = None

    def connect(self) -> bool:
        """
        Establish connection to Redis and check connectivity.
        Returns True if connection is successful, False otherwise.
        """
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            # Test connection
            self.client.ping()
            logger.info(f"Successfully connected to Redis at {self.host}:{self.port}")
            return True
        except redis.ConnectionError as e:
            logger.exception(f"Failed to connect to Redis at {self.host}:{self.port} - {str(e)}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error connecting to Redis: {str(e)}")
            return False

    def disconnect(self):
        """Close Redis connection."""
        if self.client:
            self.client.close()
            logger.info("Redis connection closed")

    def is_connected(self) -> bool:
        """Check if Redis connection is active."""
        try:
            if self.client:
                self.client.ping()
                return True
            return False
        except Exception as e:
            logger.warning(f"Redis connection check failed: {str(e)}")
            return False

    def get(self, key: str) -> str | None:
        """Get value from Redis."""
        if not self.is_connected():
            logger.error("Redis not connected")
            return None
        return self.client.get(key)

    def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """Set value in Redis with optional TTL."""
        if not self.is_connected():
            logger.error("Redis not connected")
            return False
        self.client.set(key, value, ex=ttl)
        return True
