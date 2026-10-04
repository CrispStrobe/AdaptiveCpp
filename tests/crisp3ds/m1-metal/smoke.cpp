#include <sycl/sycl.hpp>
#include <cmath>
#include <iostream>
int main() {
  sycl::queue q{sycl::gpu_selector_v};
  auto d=q.get_device();
  if (!d.is_gpu() || d.get_backend()!=sycl::backend::metal) return 2;
  constexpr int n=1024;
  float *out=sycl::malloc_shared<float>(n*4,q);
  if (!out) return 3;
  q.parallel_for(sycl::range<1>{n},[=](sycl::id<1> ix) {
    const int i=ix[0];
    sycl::float3 a(1.f+float(i)*.001f, .5f, .25f);
    sycl::float3 b(.2f, 1.2f, -.3f);
    auto cross=sycl::cross(a,b);
    auto normal=cross/sycl::length(cross);
    out[4*i]=normal.x();out[4*i+1]=normal.y();out[4*i+2]=normal.z();
    out[4*i+3]=sycl::dot(normal,a);
  }).wait_and_throw();
  double max_error=0;
  for(int i=0;i<n;++i) {
    double ax=1.+i*.001, ay=.5, az=.25;
    double x=ay*(-.3)-az*1.2, y=az*.2-ax*(-.3),z=ax*1.2-ay*.2;
    double norm=std::sqrt(x*x+y*y+z*z);
    double expected[4]={x/norm,y/norm,z/norm,0};
    for(int k=0;k<4;++k) {
      if(!std::isfinite(out[4*i+k])) return 4;
      max_error=std::max(max_error,std::abs(out[4*i+k]-expected[k]));
    }
  }
  std::cout<<"device="<<d.get_info<sycl::info::device::name>()<<"; gpu=1; backend=metal; normals="<<n<<"; maximum_error="<<max_error<<"\n";
  sycl::free(out,q);
  return max_error<=1e-5 ? 0 : 5;
}
