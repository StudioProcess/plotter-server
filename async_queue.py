import asyncio

# Like asyncio.Queue with support for reordering and removing elements
class Queue(asyncio.Queue):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order = []
        
    def _rebuild(self):
        # remove all items
        try:
            while True: super().get_nowait()
        except asyncio.QueueEmpty:
            pass
        # add items in new order
        for item in self.order:
            try:
               super().put_nowait(item)
            except asyncio.QueueFull:
                pass
    
    # get the current queue as list
    def list(self):
        return self.order.copy()
    
    # swap two items by index; supports negative indices
    def swap(self, idx1, idx2):
        if idx1 < -len(self.order) or idx1 > len(self.order)-1:
            raise IndexError('index 1 out of bounds')
        if idx2 < -len(self.order) or idx2 > len(self.order)-1:
            raise IndexError('index 2 out of bounds')
        if (idx1 == idx2): return
        self.order[idx1], self.order[idx2] = self.order[idx2], self.order[idx1]
        self._rebuild()
    
    # move an item to new position in queue
    def move(self, idx, new_idx):
        if idx < -len(self.order) or idx > len(self.order)-1:
            raise IndexError('index out of bounds')
        if new_idx < -len(self.order) or new_idx > len(self.order)-1:
            raise IndexError('target index out of bounds')
        
        # normalize negative indices
        if idx < 0: idx = len(self.order) + idx
        if new_idx < 0: new_idx = len(self.order) + new_idx
        
        if (idx == new_idx): return
        item = self.order.pop(idx)
        self.order.insert(new_idx, item)
        self._rebuild()
    
    # remove an item from the queue; supports negative indices
    def pop(self, idx = -1):
        if idx < -len(self.order) or idx > len(self.order)-1:
            raise IndexError('index out of bounds')
        item = self.order.pop(idx)
        # print('remove item', item)
        self._rebuild()
        return item
    
    # insert an item at an arbitrary position into the queue
    def insert(self, idx, item):
        if idx < -len(self.order) or idx > len(self.order):
            raise IndexError('index out of bounds')
        self.order.insert(idx, item)
        self._rebuild()
        
    def put_nowait(self, item):
        # print('put_nowait')
        super().put_nowait(item)
        self.order.append(item)
    
    def get_nowait(self):
        # print('get_nowait')
        item = super().get_nowait()
        self.order.pop(0)
        return item
    
    # no need to implement get() and put()
    # as these are implemented in terms of get_nowait() and put_nowait()


if __name__ == '__main__':
    import unittest
    
    class Test(unittest.IsolatedAsyncioTestCase):
        def get_all(self, q):
            out = []
            while not q.empty():
                out.append( q.get_nowait() )
            return out
        
        async def test_put(self):
            q = Queue()
            await q.put('one')
            await q.put('two')
            await q.put('three')
            self.assertEqual(q.list(), ['one', 'two', 'three'])
            self.assertEqual( self.get_all(q), ['one', 'two', 'three'])
        
        async def test_put_nowait(self):
            q = Queue()
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            self.assertEqual(q.list(), ['one', 'two', 'three'])
            self.assertEqual( self.get_all(q), ['one', 'two', 'three'])
        
        async def test_get(self):
            q = Queue()
            get_task = asyncio.gather(
                asyncio.create_task(q.get()),
                asyncio.create_task(q.get()),
                asyncio.create_task(q.get())
            )
            await q.put('one')
            await q.put('two')
            await q.put('three')
            self.assertEqual( await get_task, ['one', 'two', 'three'] )
        
        async def test_get_nowait(self):
            q = Queue()
            with self.assertRaises(asyncio.QueueEmpty):
                q.get_nowait()
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            self.assertEqual( q.get_nowait(), 'one' )
            self.assertEqual( q.get_nowait(), 'two' )
            self.assertEqual( q.get_nowait(), 'three' )
            with self.assertRaises(asyncio.QueueEmpty):
                q.get_nowait()
        
        async def test_pop(self):
            q = Queue()
            with self.assertRaises(IndexError):
                q.pop(0)
            
            q.put_nowait('one')
            with self.assertRaises(IndexError): q.pop(1)
            with self.assertRaises(IndexError): q.pop(-2)
            self.assertEqual(q.pop(0), 'one')
            self.assertEqual(q.list(), [])
            
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            self.assertEqual(q.pop(1), 'two')
            self.assertEqual(q.list(), ['one', 'three'])
            self.assertEqual(self.get_all(q), ['one', 'three'])
            self.assertEqual(q.empty(), True)
            
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            self.assertEqual(q.pop(0), 'one')
            self.assertEqual(q.pop(-1), 'three')
            self.assertEqual(q.list(), ['two'])
            self.assertEqual(self.get_all(q), ['two'])
            
        async def test_insert(self):
            q = Queue()
            q.put_nowait('one')
            q.put_nowait('three')
            q.insert(1, 'two')
            self.assertEqual(q.list(), ['one', 'two', 'three'])
            self.assertEqual(self.get_all(q), ['one', 'two', 'three'])
            
            q.insert(0, 'one')
            q.insert(1, 'two')
            q.insert(2, 'three')
            q.insert(0, 'zero')
            self.assertEqual(q.list(), ['zero', 'one', 'two', 'three'])
            self.assertEqual(self.get_all(q), ['zero', 'one', 'two', 'three'])
            
            with self.assertRaises(IndexError): q.insert(-1, 'one')
            with self.assertRaises(IndexError): q.insert(1, 'one')
            q.insert(0, 'one')
            self.assertEqual(q.list(), ['one'])
            self.assertEqual(self.get_all(q), ['one'])
            
        async def test_swap(self):
            q = Queue()
            q.put_nowait('zero')
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            q.swap(1, 2)
            self.assertEqual(q.list(), ['zero', 'two', 'one', 'three'])
            self.assertEqual(self.get_all(q), ['zero', 'two', 'one', 'three'])
            
            q.put_nowait('zero')
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            q.swap(-1, 1)
            self.assertEqual(q.list(), ['zero', 'three', 'two', 'one'])
            self.assertEqual(self.get_all(q), ['zero', 'three', 'two', 'one'])
            
            q.put_nowait('zero')
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            with self.assertRaises(IndexError): q.swap(0, 4)
            with self.assertRaises(IndexError): q.swap(4, 0)
            with self.assertRaises(IndexError): q.swap(0, -5)
            with self.assertRaises(IndexError): q.swap(-5, 0)
            
            q.swap(0, 0)
            q.swap(1, 1)
            q.swap(2, 2)
            q.swap(3, 3)
            self.assertEqual(q.list(), ['zero', 'one', 'two', 'three'])
            self.assertEqual(self.get_all(q), ['zero', 'one', 'two', 'three'])
            
            q.put_nowait('zero')
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            q.swap(1, 0)
            self.assertEqual(q.list(), ['one', 'zero', 'two', 'three'])
            self.assertEqual(self.get_all(q), ['one', 'zero', 'two', 'three'])
            
            q.put_nowait('zero')
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            q.swap(1, -1)
            self.assertEqual(q.list(), ['zero', 'three', 'two', 'one'])
            self.assertEqual(self.get_all(q), ['zero', 'three', 'two', 'one'])
        
        async def test_move(self):
            q = Queue()
            q.put_nowait('zero')
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            with self.assertRaises(IndexError): q.move(0, 4)
            with self.assertRaises(IndexError): q.move(0, -5)
            with self.assertRaises(IndexError): q.move(4, 0)
            with self.assertRaises(IndexError): q.move(-5, 0)
            q.move(1, 1)
            self.assertEqual(q.list(), ['zero', 'one', 'two', 'three'])
            self.assertEqual(self.get_all(q), ['zero', 'one', 'two', 'three'])
            
            # move top to bottom
            q.put_nowait('zero')
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            q.move(0, -1)
            self.assertEqual(q.list(), ['one', 'two', 'three', 'zero'])
            self.assertEqual(self.get_all(q), ['one', 'two', 'three', 'zero'])
            
            # move bottom to top
            q.put_nowait('zero')
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            q.move(-1, 0)
            self.assertEqual(q.list(), ['three', 'zero', 'one', 'two'])
            self.assertEqual(self.get_all(q), ['three', 'zero', 'one', 'two'])
            
            # swap items next to each other
            q.put_nowait('zero')
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            q.move(1, 2)
            self.assertEqual(q.list(), ['zero', 'two', 'one', 'three'])
            self.assertEqual(self.get_all(q), ['zero', 'two', 'one', 'three'])
            
            # move to bottom
            q.put_nowait('zero')
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            q.move(1, -1)
            self.assertEqual(q.list(), ['zero', 'two', 'three', 'one'])
            self.assertEqual(self.get_all(q), ['zero', 'two', 'three', 'one'])
            
            # move to top
            q.put_nowait('zero')
            q.put_nowait('one')
            q.put_nowait('two')
            q.put_nowait('three')
            q.move(2, 0)
            self.assertEqual(q.list(), ['two', 'zero', 'one', 'three'])
            self.assertEqual(self.get_all(q), ['two', 'zero', 'one', 'three'])
        
    unittest.main()
    