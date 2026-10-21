import asyncio
import unittest
from range_collection import collect_numbers, parse_range


class CollectionTests(unittest.IsolatedAsyncioTestCase):
    async def run_sequence(self, values, **kwargs):
        iterator = iter(values)
        saved = []
        async def fetch(rid):
            return next(iterator), None
        async def record(number):
            saved.append(number)
        result = await collect_numbers('994', fetch, record, asyncio.Event(), interval=0, **kwargs)
        return result, saved

    async def test_unique_numbers_and_duplicate_stop(self):
        result, saved = await self.run_sequence(['+994501234567', '994501234568'] + ['994501234567'] * 3)
        self.assertEqual(result.reason, 'repeated')
        self.assertEqual(result.requests, 5)
        self.assertEqual(result.numbers, ['+994501234567', '+994501234568'])
        self.assertEqual(saved, result.numbers)

    async def test_empty_stop_and_limit(self):
        result, saved = await self.run_sequence([None] * 3)
        self.assertEqual((result.reason, result.requests, saved), ('empty', 3, []))
        result, _ = await self.run_sequence(['994501234567', '994501234568'], limit=2)
        self.assertEqual((result.reason, result.requests), ('limit', 2))

    async def test_mismatched_and_invalid_numbers_not_exported(self):
        for value in ['+1234567890', '994hello123456', '994']:
            result, saved = await self.run_sequence([value])
            self.assertEqual((result.reason, saved, result.numbers), ('mismatch', [], []))

    async def test_stop_preserves_inflight_result(self):
        stop = asyncio.Event()
        saved = []
        async def fetch(rid):
            stop.set()
            return '994501234567', None
        async def record(number): saved.append(number)
        result = await collect_numbers('994', fetch, record, stop, interval=0)
        self.assertEqual((result.reason, result.requests), ('stopped', 1))
        self.assertEqual(saved, ['+994501234567'])
        result = await collect_numbers('994', fetch, record, stop, interval=0)
        self.assertEqual(result.requests, 0)

    async def test_timeout_and_storage_failure(self):
        async def fetch(rid): await asyncio.Event().wait()
        async def record(number): raise OSError('test storage error')
        result = await collect_numbers('994', fetch, record, asyncio.Event(), timeout=0.01)
        self.assertEqual(result.reason, 'error')
        async def valid(rid): return '994501234567', None
        result = await collect_numbers('994', valid, record, asyncio.Event(), interval=0)
        self.assertEqual(result.reason, 'storage')
        self.assertEqual(result.numbers, ['+994501234567'])

    def test_strict_range_input(self):
        self.assertEqual(parse_range(' 234xxx '), '234')
        self.assertEqual(parse_range('26134'), '26134')
        for bad in ['abc234', '23X45', '', 'X', '1'*16, '../234', '234 XXX']:
            with self.assertRaises(ValueError): parse_range(bad)


if __name__ == '__main__': unittest.main()
