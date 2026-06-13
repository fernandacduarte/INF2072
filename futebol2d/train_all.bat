@echo off
REM Batch script to train IQL, VDN, and QMIX with shared parameters
REM Usage: train_all.bat [other train.py args except --algo]

setlocal

REM Pass all arguments except algorithm
set ARGS=%*

REM Train IQL
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python train.py --algo iql %ARGS%

REM Train VDN
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python train.py --algo vdn %ARGS%

REM Train QMIX
%USERPROFILE%\AppData\Local\Programs\Python\Python312\python train.py --algo qmix %ARGS%

endlocal
