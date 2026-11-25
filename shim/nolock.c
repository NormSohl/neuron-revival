#define _GNU_SOURCE
/* Preload for PERF mode: real-time scheduling goes through to the real libraries (the
   launcher caps it with ulimit -r); only memory locking is faked. Reports crash addresses.
   The audio thread asks for SCHED_RR at sched_get_priority_max (99), above the ulimit -r cap, so the
   request failed and its following nice(20) left the busiest thread at the lowest priority: it underran
   ~15 times a minute on the Twist (2026-11-24). Requests above the cap are now clamped to the cap. */
#include <sched.h>
#include <pthread.h>
#include <signal.h>
#include <unistd.h>
#include <stdio.h>
#include <dlfcn.h>
#include <sys/resource.h>
static int clamp(int pr){ struct rlimit rl; if(getrlimit(RLIMIT_RTPRIO,&rl)==0 && rl.rlim_cur!=RLIM_INFINITY && pr>(int)rl.rlim_cur) pr=(int)rl.rlim_cur; return pr; }
int pthread_setschedparam(pthread_t t, int pol, const struct sched_param *p){
  static int (*real)(pthread_t,int,const struct sched_param*);
  if(!real) real=(int(*)(pthread_t,int,const struct sched_param*))dlsym(RTLD_NEXT,"pthread_setschedparam");
  struct sched_param q=*p; if(pol!=SCHED_OTHER) q.sched_priority=clamp(q.sched_priority); return real(t,pol,&q); }
int sched_setscheduler(pid_t pid, int pol, const struct sched_param *p){
  static int (*real)(pid_t,int,const struct sched_param*);
  if(!real) real=(int(*)(pid_t,int,const struct sched_param*))dlsym(RTLD_NEXT,"sched_setscheduler");
  struct sched_param q=*p; if(pol!=SCHED_OTHER) q.sched_priority=clamp(q.sched_priority); return real(pid,pol,&q); }
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
