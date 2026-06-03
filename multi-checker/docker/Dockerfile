FROM skogsbaer/praktomat-checker-base:latest

# Haskell stuff
# Install stack
RUN curl -sSL https://get.haskellstack.org/ | sh

# Install haskell packages needed by the test routines.
# The resolver must match the one given in the stack.yaml file
# from praktomat-tests/haskell-advanced-prog/common and from
# ~/Teaching/AdvancedProg-Praktikum/config-common
RUN stack --resolver lts-24.3 install base
RUN stack --resolver lts-24.3 install containers directory filepath template-haskell mtl text
RUN stack --resolver lts-24.3 install happy primitive safe syb vector
RUN stack --resolver lts-24.3 install haskell-src-exts
RUN stack --resolver lts-24.3 install haskell-src-meta
RUN stack --resolver lts-24.3 install main-tester
RUN stack --resolver lts-24.3 install call-stack HUnit

# Install Gradle
RUN apt-get update && apt-get install -yq \
  openjdk-21-jdk \
  zip \
  && rm -rf /var/lib/apt/lists/*
ARG GRADLE_VERSION=8.13
ADD https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip /gradle.zip
RUN mkdir /opt/gradle
RUN unzip -d /opt/gradle /gradle.zip
RUN rm /gradle.zip
RUN chmod -R 775 /opt/gradle/gradle-${GRADLE_VERSION}/bin
RUN ln -s /opt/gradle/gradle-${GRADLE_VERSION}/bin/* /usr/local/bin

# Install Gradle dependencies
COPY ./get-deps.gradle.kts /get-gradle-deps/build.gradle.kts
RUN cd /get-gradle-deps && gradle --no-daemon getDeps
RUN rm -rf /get-gradle-deps

# Python
# Packages
RUN apt-get update && apt-get install -yq \
  python3-yaml \
  && rm -rf /var/lib/apt/lists/*
RUN pip3 install --break-system-packages libPyshell==0.5.0 aiofiles aiohttp

# WYPP, version 2.2.1 plus some fixes (2026-03-26)
RUN mkdir /wypp
ADD ./git-clone /git-clone
RUN bash /git-clone https://github.com/skogsbaer/write-your-python-program.git 324674a3f12b0f4d5dc75d5123b9842f9aee54ea /wypp
RUN rm -rf /wypp/.git

# llm-tutor
RUN mkdir /llm-tutor
ADD ./git-clone /git-clone
RUN bash /git-clone https://github.com/alaref-tasnim/LLM-Tutor.git 432f5fd7bc52bda98709f2e2cbc755946a8febd4 /llm-tutor
RUN rm -rf /llm-tutor/.git

# Install packages for llm-tutor .toml datei
RUN pip3 install --break-system-packages -e /llm-tutor

# Our checker scripts
ADD checker /checker