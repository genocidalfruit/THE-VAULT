Tags : [[Tech]], [[Books]]

# Using Threads in C++

`#include <iostream>`
`#include <thread>`

`void hello(){`
  `std::cout<<"Hello Concurrent World!";`
`}`

`int main(){`
  `std::thread t(hello);`
  `t.join();`
`}`

Thread is initialised with a function and then joined for program execution.

A thread can be initialised with an object. In this case the function is passed to the thread and the function is run by the thread.
![[Pasted image 20260116224734.png]]