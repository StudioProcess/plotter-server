import asyncio
import types

# Calls fn in intervals given by the interval parameter (in seconds)
# fn is called with an argument giving the elapsed time since start
# Returns a Task object

def async_interval(fn, interval, end = 0):
    async def run(fn, interval):
        try:
            start = loop.time()
            while True:
                await asyncio.sleep(interval)
                fn( loop.time() - start )
        except asyncio.CancelledError:
            pass
    
    def stop():
        try: task.cancel()
        except asyncio.CancelledError: pass
    
    loop = asyncio.get_running_loop()
    task = asyncio.create_task( run(fn, interval) )
    if (end > 0): loop.call_later(end, stop)
    return task

if __name__ == '__main__':
    import unittest
            
    class Test(unittest.IsolatedAsyncioTestCase):
        async def test_cancel(self):
            def empty(): pass
            i = async_interval(empty, 1)
            await asyncio.sleep(0) # need to wait, otherwise CancelledError is raised anyway
            i.cancel()
            await i # wait for interval completion
            self.assertEqual(i.done(), True)
            # cancelled() is False since the wrapped coroutine doesn't propagate the CancelledError
            self.assertEqual(i.cancelled(), False)
            
        async def test_interval(self):
            times = []
            def fn(time): times.append(time)
            
            i = async_interval(fn, 1/4)
            await asyncio.sleep(1)
            i.cancel()
            await i
            # print(times)
            self.assertEqual(len(times), 3)
            self.assertAlmostEqual(times[0], 0.25, places=2)
            self.assertAlmostEqual(times[1], 0.50, places=2)
            self.assertAlmostEqual(times[2], 0.75, places=2)
        
        async def test_end(self):
            times = []
            def fn(time): times.append(time)
            
            i = async_interval(fn, 1/4, 1)
            await i
            self.assertEqual(len(times), 3)
            self.assertAlmostEqual(times[0], 0.25, places=2)
            self.assertAlmostEqual(times[1], 0.50, places=2)
            self.assertAlmostEqual(times[2], 0.75, places=2)
            
    unittest.main()