FROM python:3.7-slim

LABEL maintainer="Ladybug Tools" email="info@ladybug.tools"

ENV WORKDIR='/home/ladybugbot'
ENV RUNDIR="${WORKDIR}/run"
ENV LIBRARYDIR="${WORKDIR}/ladybug-radiance"
ENV RAYPATH=".:${WORKDIR}/lib"
ENV BINPATH="${WORKDIR}/bin"
ENV PATH="${WORKDIR}/.local/bin:${BINPATH}:${PATH}"

RUN apt-get update \
    && apt-get -y install --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN adduser ladybugbot --uid 1000 --disabled-password --gecos ""
USER ladybugbot
WORKDIR ${WORKDIR}

# Expects a decompressed radiance folder in the build context
COPY radiance/usr/local/radiance/bin ${BINPATH}
COPY radiance/usr/local/radiance/lib ${WORKDIR}/lib

# Install ladybug-radiance
COPY ladybug_radiance ${LIBRARYDIR}/ladybug_radiance
COPY .git ${LIBRARYDIR}/.git
COPY README.md ${LIBRARYDIR}
COPY requirements.txt ${LIBRARYDIR}
COPY display-requirements.txt ${LIBRARYDIR}
COPY setup.py ${LIBRARYDIR}
COPY setup.cfg ${LIBRARYDIR}
COPY LICENSE ${LIBRARYDIR}

# Switch user back to modify packages
USER root
RUN pip3 install --no-cache-dir setuptools wheel \
    && pip3 install --no-cache-dir ./ladybug-radiance[display] \
    && apt-get -y --purge remove git \
    && apt-get -y clean \
    && apt-get -y autoremove \
    && rm -rf ${LIBRARYDIR}/.git

USER ladybugbot
# Set workdir
RUN mkdir -p ${RUNDIR}
WORKDIR ${RUNDIR}
