@echo off
title Times07 Auto Push
echo --------------------------------------
echo GitHub Push On-The-Way...
echo --------------------------------------
git add .
git commit -m "New Article Published"
git push origin main
echo --------------------------------------
echo SUCCESS! Website Par Live Ho Gaya!
echo --------------------------------------
pause