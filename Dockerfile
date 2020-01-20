FROM continuumio/miniconda3

RUN conda create -n env python=3.7.4
RUN echo "source activate env" > ~/.bashrc
ENV PATH /opt/conda/envs/env/bin:$PATH