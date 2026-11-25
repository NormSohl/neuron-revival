/* Preload for running the Neuron binary on a shared machine: accept but ignore
   real-time scheduling and memory locking requests; report crash addresses. */
#include <sched.h>
#include <pthread.h>
#include <signal.h>
#include <unistd.h>
#include <stdio.h>
int pthread_setschedparam(pthread_t t, int policy, const struct sched_param *p){ return 0; }
int sched_setscheduler(int pid, int policy, const struct sched_param *p){ return 0; }
int mlockall(int flags){ return 0; }
static void hex(char *b,unsigned v){ int i; for(i=7;i>=0;i--){ b[i]="0123456789abcdef"[v&15]; v>>=4; } }
static void onsegv(int sig, siginfo_t *si, void *ctx){
  unsigned *g=(unsigned*)((char*)ctx+20);           /* i386 ucontext: uc_flags,uc_link,uc_stack(12) -> mcontext gregs */
  char m[]="\n[nort] SIGSEGV eip=xxxxxxxx addr=xxxxxxxx esp=xxxxxxxx\n";
  hex(m+20,g[14]); hex(m+34,(unsigned)si->si_addr); hex(m+47,g[7]);
  write(2,m,sizeof m-1); _exit(139); }
__attribute__((constructor)) static void init(void){
  struct sigaction sa; int i; char *p=(char*)&sa; for(i=0;i<(int)sizeof sa;i++) p[i]=0;
  sa.sa_sigaction=onsegv; sa.sa_flags=SA_SIGINFO; sigaction(SIGSEGV,&sa,0); setvbuf(stdout,0,_IONBF,0); }
