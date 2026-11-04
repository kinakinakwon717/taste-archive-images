#!/bin/zsh
# 사용법: mux.sh silent.mp4 music.mp3 out_dir   (맥: PATH=/tmp/tsv/bin:$PATH)
S=$1; M=$2; O=$3; mkdir -p $O
ffmpeg -v error -y -i "$S" -i "$M" -filter_complex "[1:a]silenceremove=start_periods=1:start_threshold=-35dB,atrim=0:16.5,asetpts=N/SR/TB,afade=t=in:d=0.05,afade=t=out:st=15.8:d=0.7,loudnorm=I=-15:TP=-1.5:LRA=11,aresample=44100[a]" -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 160k -shortest -movflags +faststart "$O/upload.mp4"
ffmpeg -v error -y -ss 1.6 -i "$O/upload.mp4" -frames:v 1 -q:v 2 "$O/cover.jpg"
ls -la "$O"
