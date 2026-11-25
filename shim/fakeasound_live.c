/* Stand-in libasound.so.2 for the Hartmann Neuron binary (ALSA 0.9 "old" API).
   PCM: accepts any config; mmap_writei paces to real time and appends raw
        interleaved samples to $NEURON_AUDIO_OUT (default /tmp/neuron_audio.raw).
   RawMIDI: output bytes go to /tmp/neuron_midi_out.bin; input reads /tmp/neuron_midi_in (FIFO) if present. */
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/time.h>
#include <stdio.h>
typedef struct { int ch, fmt, rate, period, buffer; int fd; double next; long long frames; } pcm_t;
static double now(void){ struct timeval tv; gettimeofday(&tv,0); return tv.tv_sec+tv.tv_usec*1e-6; }
static pcm_t *last;
int snd_pcm_open(void **p, const char *name, int stream, int mode){
  pcm_t *h=calloc(1,sizeof *h); h->ch=2; h->fmt=10; h->rate=44100; h->period=256; h->buffer=512;
  h->fd=open("/var/tmp/neuron_audio.fifo",O_WRONLY); if(h->fd>=0) fcntl(h->fd,1031/*F_SETPIPE_SZ*/,4096);
  *p=h; last=h; fprintf(stderr,"[fakeasound] pcm_open %s\n",name); return 0; }
int snd_pcm_close(void *p){ return 0; }
int snd_pcm_hw_params_sizeof(void){ return 256; }
int snd_pcm_sw_params_sizeof(void){ return 256; }
int snd_pcm_status_sizeof(void){ return 256; }
int snd_pcm_hw_params_any(void *p, void *hw){ return 0; }
int snd_pcm_hw_params_set_access(void *p, void *hw, int a){ return 0; }
int snd_pcm_hw_params_set_format(void *p, void *hw, int f){ ((pcm_t*)p)->fmt=f; return 0; }
int snd_pcm_hw_params_set_channels(void *p, void *hw, unsigned c){ ((pcm_t*)p)->ch=c; return 0; }
unsigned snd_pcm_hw_params_set_rate_near(void *p, void *hw, unsigned r, int *dir){ ((pcm_t*)p)->rate=r; return r; }
unsigned snd_pcm_hw_params_set_buffer_time_near(void *p, void *hw, unsigned us, int *dir){ pcm_t*h=p; h->buffer=(int)((double)us*h->rate/1e6+0.5); return us; }
unsigned snd_pcm_hw_params_set_period_time_near(void *p, void *hw, unsigned us, int *dir){ pcm_t*h=p; h->period=(int)((double)us*h->rate/1e6+0.5); return us; }
unsigned long snd_pcm_hw_params_get_buffer_size(void *hw){ return last?last->buffer:512; }
unsigned long snd_pcm_hw_params_get_period_size(void *hw, int *dir){ return last?last->period:256; }
int snd_pcm_hw_params(void *p, void *hw){ pcm_t*h=p; fprintf(stderr,"[fakeasound] hw_params ch=%d fmt=%d rate=%d period=%d buffer=%d\n",h->ch,h->fmt,h->rate,h->period,h->buffer); return 0; }
int snd_pcm_sw_params_current(void *p, void *sw){ return 0; }
int snd_pcm_sw_params_set_start_threshold(void *p, void *sw, unsigned long v){ return 0; }
int snd_pcm_sw_params_set_avail_min(void *p, void *sw, unsigned long v){ return 0; }
int snd_pcm_sw_params_set_xfer_align(void *p, void *sw, unsigned long v){ return 0; }
int snd_pcm_sw_params(void *p, void *sw){ return 0; }
int snd_pcm_prepare(void *p){ return 0; }
int snd_pcm_resume(void *p){ return 0; }
int snd_pcm_status(void *p, void *st){ return 0; }
/* report a clock that barely moves, so the engine's own CPU-load meter reads ~0% */
void snd_pcm_status_get_tstamp(void *st, struct timeval *tv){ static long sec=0, usec=0; usec+=10; if(usec>=1000000){usec-=1000000; sec++;} tv->tv_sec=sec; tv->tv_usec=usec; }
int snd_pcm_format_width(int f){ return (f==10||f==11)?32:(f==2||f==3)?16:32; }
long snd_pcm_mmap_writei(void *p, const void *buf, unsigned long frames){
  pcm_t *h=p; double t=now();
  if(h->next==0||h->next<t-0.1) h->next=t;
  if(h->fd>=0){ static short tmp[2*4096]; const int *in=buf; unsigned long i,n=frames>4096?4096:frames;
    for(i=0;i<n;i++){ tmp[2*i]=in[i*h->ch]>>15; tmp[2*i+1]=in[i*h->ch+1]>>15; }
    write(h->fd,tmp,n*4); }
  h->frames+=frames; h->next+=(double)frames/h->rate;
  { static double t0=0,last=0; static int lf=-1; double tn=now(); if(t0==0) t0=tn;
    if(tn-last>=1.0){ char b[160]; int k; if(lf<0) lf=open("/var/tmp/neuron_stats.txt",O_WRONLY|O_CREAT|O_APPEND,0644);
      k=sprintf(b,"wall %.1f audio %.2f call_frames %lu\n",tn-t0,(double)h->frames/h->rate,frames); write(lf,b,k); last=tn;  /* no fsync: it can stall the audio thread */ } }
  if(h->fd<0){ double d=h->next-now()-(double)h->buffer/h->rate/2; if(d>0) usleep((unsigned)(d*1e6)); }
  return (long)frames; }
/* rawmidi */
static int mout=-1, min=-1;
int snd_rawmidi_open(void **in, void **out, const char *name, int mode){
  if(in) *in=(void*)1; if(out) *out=(void*)2;
  mout=open("/var/tmp/neuron_midi_out.bin",O_WRONLY|O_CREAT|O_TRUNC,0644);
  fprintf(stderr,"[fakeasound] rawmidi_open %s\n",name); return 0; }
long snd_rawmidi_read(void *h, void *buf, size_t n){
  for(;;){ if(min<0) min=open("/var/tmp/neuron_midi_in",O_RDONLY);
    if(min>=0){ long r=read(min,buf,n); if(r>0) return r; close(min); min=-1; }
    sleep(1); } }
long snd_rawmidi_write(void *h, const void *buf, size_t n){ if(mout>=0){ write(mout,buf,n);} return (long)n; }
int snd_rawmidi_drain(void *h){ return 0; }
int snd_rawmidi_close(void *h){ return 0; }
const char *snd_strerror(int e){ return "fakeasound error"; }
