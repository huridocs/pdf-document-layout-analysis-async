from unittest.mock import MagicMock


class FakeConnection:
    def __init__(self, pool):
        self.pool = pool

    def execute(self, sql, params=None):
        self.pool.executed.append((sql, params))
        return MagicMock(fetchall=MagicMock(return_value=[("id",)]))

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakePool:
    def __init__(self):
        self.executed = []

    def check(self):
        pass

    def connection(self):
        return FakeConnection(self)

    def close(self):
        pass
