Tags : [[Tech]]

# Search for element that appears once in a sorted array
- Indexing without the additional element means the number of items in list is even
- If the item is on the left side - Indexing will be skewed right (array elements in mid and mid-1 will be the same)
- If item is on the right side - Indexing in the middle will remain the same
Perform binary search for the side the item is on based on the above conditions and return `nums[low]` at the end of the while loop (`while low<high`)