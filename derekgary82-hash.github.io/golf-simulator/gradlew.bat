@echo off
REM Gradle start up script for Windows
setlocal

:: Resolve links - https://stackoverflow.com/a/18410985/1184886
set PRG=%~dp0\..\gradlew.bat

REM Default JVM options
set DEFAULT_JVM_OPTS=-Xmx2g

set WRAPPER_JAR=%~dp0\gradle\wrapper\gradle-wrapper.jar
if not exist "%WRAPPER_JAR%" (
  echo Gradle wrapper jar not found. The script will attempt to download it from the Gradle distribution.
)

java -cp "%WRAPPER_JAR%" org.gradle.wrapper.GradleWrapperMain %*
endlocal
