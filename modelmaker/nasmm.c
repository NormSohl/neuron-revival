// nasmm: run Hartmann MODELmaker's NASAnalysis.dll (win32) headless on Linux/x86.
// Minimal PE loader + kernel32 stubs + fake JNIEnv.  Build: gcc -m32 -O1 -o nasmm nasmm.c
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>

#define WINAPI __attribute__((stdcall))
typedef uint32_t DW;
static int verbose = 0;
#define V(...) do{ if(verbose) fprintf(stderr, __VA_ARGS__);}while(0)

/* ---------- handles ---------- */
#define HBASE 0x100
static DW mkh(int fd){ return fd + HBASE; }
static int hfd(DW h){ return (int)h - HBASE; }

/* ---------- kernel32 ---------- */
static void WINAPI k_ECS(void*p){}
static void WINAPI k_LCS(void*p){}
static void WINAPI k_ICS(void*p){}
static void WINAPI k_DCS(void*p){}
static DW WINAPI k_GetCurrentThread(void){ return 0xfffffffe; }
static DW WINAPI k_GetCurrentProcess(void){ return 0xffffffff; }
static DW WINAPI k_DuplicateHandle(DW a, DW src, DW b, DW*dst, DW acc, DW inh, DW opt){ if(dst)*dst=src; return 1; }
static void* tls[64]; static int ntls=0;
static DW WINAPI k_TlsAlloc(void){ return ntls<64? ntls++ : 0xffffffff; }
static DW WINAPI k_TlsFree(DW i){ return 1; }
static void* WINAPI k_TlsGetValue(DW i){ return i<64? tls[i]:0; }
static DW WINAPI k_TlsSetValue(DW i, void*v){ if(i<64) tls[i]=v; return 1; }
static DW WINAPI k_GetLastError(void){ return 0; }
static void WINAPI k_ExitProcess(DW c){ fprintf(stderr,"ExitProcess(%u)\n",c); exit(c); }
static void* WINAPI k_GlobalAlloc(DW f, DW n){ return calloc(1, n?n:1); }
static void* WINAPI k_GlobalFree(void*p){ free(p); return 0; }
static DW WINAPI k_GetStdHandle(DW n){ int fd = (n==0xfffffff6)?0:(n==0xfffffff5)?1:2; return mkh(fd); }
static DW WINAPI k_GetFullPathNameA(const char*n, DW len, char*buf, char**fp){
  size_t l=strlen(n); if(l+1>len) return l+1; strcpy(buf,n);
  if(fp){ char*s=strrchr(buf,'/'); if(!s) s=strrchr(buf,'\\'); *fp = s? s+1: buf; } return l; }
static DW WINAPI k_SetFilePointer(DW h, int32_t lo, int32_t*hi, DW m){
  off_t r = lseek(hfd(h), lo, m==0?SEEK_SET:m==1?SEEK_CUR:SEEK_END); if(hi)*hi=0;
  V("SetFilePointer(%d,%d,%u)=%ld\n",hfd(h),lo,m,(long)r); return r<0?0xffffffff:(DW)r; }
static DW WINAPI k_WriteFile(DW h, const void*b, DW n, DW*w, void*o){
  ssize_t r = write(hfd(h), b, n); if(w)*w = r<0?0:r; return r>=0; }
static DW WINAPI k_ReadFile(DW h, void*b, DW n, DW*rd, void*o){
  ssize_t r = read(hfd(h), b, n); if(rd)*rd = r<0?0:r; return r>=0; }
static DW WINAPI k_CloseHandle(DW h){ if(h>=HBASE+3) close(hfd(h)); return 1; }
static char* fixpath(const char*n){ char*s=strdup(n); for(char*p=s;*p;p++) if(*p=='\\')*p='/'; return s; }
static DW WINAPI k_CreateFileA(const char*name, DW acc, DW sh, void*sa, DW disp, DW fl, DW tmpl){
  int f=0; int rw = (acc&0x80000000)&&(acc&0x40000000);
  f = rw? O_RDWR : (acc&0x40000000)? O_WRONLY : O_RDONLY;
  switch(disp){case 1:f|=O_CREAT|O_EXCL;break;case 2:f|=O_CREAT|O_TRUNC;break;case 4:f|=O_CREAT;break;case 5:f|=O_TRUNC;break;}
  char*p=fixpath(name); int fd=open(p,f,0644); V("CreateFileA(%s,%x,%u)=%d\n",p,acc,disp,fd); free(p);
  return fd<0?0xffffffff:mkh(fd); }
static DW WINAPI k_GetTickCount(void){ struct timeval t; gettimeofday(&t,0); return t.tv_sec*1000+t.tv_usec/1000; }
static void WINAPI k_GetLocalTime(uint16_t*st){ time_t t=time(0); struct tm m; localtime_r(&t,&m);
  st[0]=m.tm_year+1900; st[1]=m.tm_mon+1; st[2]=m.tm_wday; st[3]=m.tm_mday; st[4]=m.tm_hour; st[5]=m.tm_min; st[6]=m.tm_sec; st[7]=0; }
static DW WINAPI k_FindFirstFileA(const char*n, void*d){ return 0xffffffff; }
static DW WINAPI k_FindNextFileA(DW h, void*d){ return 0; }
static DW WINAPI k_FindClose(DW h){ return 1; }
static DW WINAPI k_DeleteFileA(const char*n){ char*p=fixpath(n); int r=unlink(p); free(p); return r==0; }
static char* WINAPI k_GetCommandLineA(void){ return "nasmm"; }
static char envblk[4]={0,0,0,0};
static char* WINAPI k_GetEnvironmentStrings(void){ return envblk; }
static DW WINAPI k_FreeEnvironmentStringsA(void*p){ return 1; }
static DW WINAPI u_MessageBoxA(DW h, const char*t, const char*c, DW ty){ fprintf(stderr,"[MessageBox] %s: %s\n",c?c:"",t?t:""); return 1; }

struct imp { const char*name; void*fn; } imps[] = {
 {"EnterCriticalSection",k_ECS},{"LeaveCriticalSection",k_LCS},{"InitializeCriticalSection",k_ICS},{"DeleteCriticalSection",k_DCS},
 {"GetCurrentThread",k_GetCurrentThread},{"GetCurrentProcess",k_GetCurrentProcess},{"DuplicateHandle",k_DuplicateHandle},
 {"TlsAlloc",k_TlsAlloc},{"TlsFree",k_TlsFree},{"TlsGetValue",k_TlsGetValue},{"TlsSetValue",k_TlsSetValue},
 {"GetLastError",k_GetLastError},{"ExitProcess",k_ExitProcess},{"GlobalAlloc",k_GlobalAlloc},{"GlobalFree",k_GlobalFree},
 {"GetStdHandle",k_GetStdHandle},{"GetFullPathNameA",k_GetFullPathNameA},{"SetFilePointer",k_SetFilePointer},
 {"WriteFile",k_WriteFile},{"ReadFile",k_ReadFile},{"CloseHandle",k_CloseHandle},{"CreateFileA",k_CreateFileA},
 {"GetTickCount",k_GetTickCount},{"GetLocalTime",k_GetLocalTime},{"FindFirstFileA",k_FindFirstFileA},
 {"FindNextFileA",k_FindNextFileA},{"FindClose",k_FindClose},{"DeleteFileA",k_DeleteFileA},
 {"GetCommandLineA",k_GetCommandLineA},{"GetEnvironmentStrings",k_GetEnvironmentStrings},
 {"FreeEnvironmentStringsA",k_FreeEnvironmentStringsA},{"MessageBoxA",u_MessageBoxA},{0,0}};

/* ---------- fake JNI ---------- */
typedef struct { void** fns; } JEnv;
static void* jtab[300];
static void jtrap(void){ fprintf(stderr,"unhandled JNI call\n"); abort(); }
static DW WINAPI j_GetObjectClass(JEnv*e, void*o){ return 1; }
static const char* WINAPI j_GetMethodID(JEnv*e, void*c, const char*n, const char*s){ char*b=malloc(strlen(n)+strlen(s)+2); sprintf(b,"%s %s",n,s); return b; }
int last_progress=0;
static void WINAPI j_CallVoidMethodV(JEnv*e, void*o, const char*mid, char* ap){
  if(strstr(mid,"(F)") || strstr(mid,"(D)")){ double v=*(double*)ap; V("  %s -> %g\n",mid,v); }
  else { int v=*(int*)ap; if(!strncmp(mid,"nasCallback",11)) last_progress=v; else V("  %s -> %d\n",mid,v); }
}
static const char* WINAPI j_GetStringUTFChars(JEnv*e, const char*s, void*c){ return s; }
static void WINAPI j_ReleaseStringUTFChars(JEnv*e, const char*s, const char*c){}

/* ---------- PE loader ---------- */
static uint8_t* load_pe(const char*path){
  FILE*f=fopen(path,"rb"); if(!f){perror(path);exit(1);} fseek(f,0,SEEK_END); long n=ftell(f); rewind(f);
  uint8_t*d=malloc(n); fread(d,1,n,f); fclose(f);
  uint32_t pe=*(uint32_t*)(d+0x3c); uint16_t nsec=*(uint16_t*)(d+pe+6); uint16_t opt=*(uint16_t*)(d+pe+20);
  uint8_t*oh=d+pe+24; uint32_t base=*(uint32_t*)(oh+28), isz=*(uint32_t*)(oh+56), hsz=*(uint32_t*)(oh+60);
  uint8_t*m=mmap((void*)base, isz, PROT_READ|PROT_WRITE|PROT_EXEC, MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE, -1, 0);
  if(m==MAP_FAILED||m!=(uint8_t*)base){ perror("mmap at imagebase"); exit(1);} memcpy(m,d,hsz);
  uint8_t*sh=oh+opt;
  for(int i=0;i<nsec;i++,sh+=40){ uint32_t va=*(uint32_t*)(sh+12), rs=*(uint32_t*)(sh+16), ro=*(uint32_t*)(sh+20); if(rs) memcpy(m+va,d+ro,rs); }
  uint32_t irva=*(uint32_t*)(oh+96+8);
  for(uint32_t*id=(uint32_t*)(m+irva); id[3]; id+=5){
    uint32_t*thunk=(uint32_t*)(m+(id[0]?id[0]:id[4])); uint32_t*iat=(uint32_t*)(m+id[4]);
    for(;*thunk;thunk++,iat++){ const char*nm=(const char*)(m+*thunk+2); void*fn=0;
      for(struct imp*p=imps;p->name;p++) if(!strcmp(p->name,nm)) fn=p->fn;
      if(!fn){ fprintf(stderr,"missing import %s\n",nm); exit(1);} *iat=(uint32_t)fn; } }
  free(d); return m;
}
static void* getexp(uint8_t*m, const char*name){
  uint32_t pe=*(uint32_t*)(m+0x3c); uint32_t erva=*(uint32_t*)(m+pe+24+96);
  uint32_t*e=(uint32_t*)(m+erva); uint32_t nn=e[6]; uint32_t*names=(uint32_t*)(m+e[8]); uint16_t*ord=(uint16_t*)(m+e[9]); uint32_t*fns=(uint32_t*)(m+e[7]);
  for(uint32_t i=0;i<nn;i++) if(strstr((char*)m+names[i],name)) return m+fns[ord[i]];
  fprintf(stderr,"no export %s\n",name); exit(1);
}

typedef int WINAPI (*fv_t)(JEnv*,void*,const char*,void*);
typedef int WINAPI (*fi_t)(JEnv*,void*);
typedef int WINAPI (*fa_t)(JEnv*,void*,const char*,const char*,const char*,int,int,int,int,int);
typedef int WINAPI (*dm_t)(void*,DW,void*);

int main(int argc, char**argv){
  const char*dll = getenv("NASDLL")? getenv("NASDLL") : "NASAnalysis.dll";
  if(getenv("NASV")) verbose=1;
  if(argc<4){ fprintf(stderr,"usage: nasmm in.aif out_basename complexityDepth parset [isMulti] [loopStartID loopEndID]\n"
     "  writes out_basename.scape / .sphere   (recursion depth: MODELmaker complexity 8 = depth 54?)\n"); return 2; }
  uint8_t*m=load_pe(dll);
  for(int i=0;i<300;i++) jtab[i]=jtrap;
  jtab[0x7c/4]=j_GetObjectClass; jtab[0x84/4]=j_GetMethodID; jtab[0xf8/4]=j_CallVoidMethodV;
  jtab[0x2a4/4]=j_GetStringUTFChars; jtab[0x2a8/4]=j_ReleaseStringUTFChars;
  JEnv env={jtab}; JEnv*penv=&env;  // JNIEnv* points to struct whose first word is fn table
  uint32_t pe=*(uint32_t*)(m+0x3c); uint32_t ep=*(uint32_t*)(m+pe+24+16);
  int r=((dm_t)(m+ep))(m,1,0); V("DllMain=%d\n",r);
  fv_t validate=(fv_t)getexp(m,"validateSample"); fi_t init=(fi_t)getexp(m,"initNAS"); fa_t an=(fa_t)getexp(m,"analyseSample");
  char info[64];
  int st=validate((JEnv*)penv,(void*)1,argv[1],info);
  if(st){ fprintf(stderr,"validateSample: status %d\n",st); return 10+st; }
  char sc[1024], sp[1024]; snprintf(sc,sizeof sc,"%s.scape",argv[2]); snprintf(sp,sizeof sp,"%s.sphere",argv[2]);
  close(open(sc,O_CREAT|O_WRONLY|O_TRUNC,0644)); close(open(sp,O_CREAT|O_WRONLY|O_TRUNC,0644));
  int depth=atoi(argv[3]), ps=argc>4?atoi(argv[4]):0, multi=argc>5?atoi(argv[5]):0, ls=argc>6?atoi(argv[6]):0, le=argc>7?atoi(argv[7]):1;
  st=init((JEnv*)penv,(void*)1); if(st){ fprintf(stderr,"initNAS: %d\n",st); return 30; }
  int lastp=-1; long it=0;
  do { st=an((JEnv*)penv,(void*)1,argv[1],sc,sp,depth,ps,multi,ls,le); it++;
       if(last_progress!=lastp){ lastp=last_progress; fprintf(stderr,"\rprogress %d%%  ",lastp); }
  } while(st==0);
  fprintf(stderr,"\nstatus %d after %ld calls\n",st,it);
  return st==1?0:st;
}
