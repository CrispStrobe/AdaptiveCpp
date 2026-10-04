#include <sycl/sycl.hpp>
#include <cmath>
#include <iostream>
int main(){
 sycl::queue q{sycl::cpu_selector_v};
 const auto d=q.get_device();
 if(!d.is_cpu() || !d.has(sycl::aspect::fp64) || !d.has(sycl::aspect::usm_device_allocations) || !d.has(sycl::aspect::usm_host_allocations)) return 2;
 double* x=sycl::malloc_shared<double>(1024,q);
 if(!x) return 3;
 q.parallel_for(sycl::range<1>{1024},[=](sycl::id<1> i){x[i]=double(i[0])*2.0+0.25;}).wait_and_throw();
 for(int i=0;i<1024;++i) if(x[i]!=double(i)*2.0+0.25) return 4;
 std::cout<<"verified 1024 double outputs; CPU="<<d.get_info<sycl::info::device::name>()<<"\n";
 sycl::free(x,q);
 return 0;
}
