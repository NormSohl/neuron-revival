#!/bin/sh
# shim/build.sh CHROOT — build the libasound / libnort shims against the Neuron's own glibc 2.2.5
set -e
C=${1:?usage: shim/build.sh CHROOT}; D=$(dirname "$0")
F="-m32 -O2 -fPIC -shared -fno-stack-protector -fno-asynchronous-unwind-tables -D_FORTIFY_SOURCE=0 -nostdlib \
 -Wl,--hash-style=sysv -Wl,-z,norelro -Wl,-z,lazy -Wl,--build-id=none -Wl,-z,noseparate-code -Wl,--no-eh-frame-hdr"
for v in "" _vm _vm32 _live _live32; do
  gcc $F -Wl,-soname,libasound.so.2 -o "$D/libasound$v.so" "$D/fakeasound$v.c" "$C/lib/libc.so.6"
done
gcc $F -Wl,-soname,libnort.so -o "$D/libnort.so" "$D/nort.c" "$C/lib/libc.so.6"
gcc $F -Wl,-soname,libnolock.so -o "$D/libnolock.so" "$D/nolock.c" "$C/lib/libc.so.6" "$C/lib/libdl.so.2"
echo "built shims in $D"
