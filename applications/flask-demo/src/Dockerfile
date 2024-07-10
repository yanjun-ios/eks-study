FROM public.ecr.aws/docker/library/python:alpine3.18 
WORKDIR /app 
RUN pip install Flask 
RUN apk update && apk upgrade --no-cache 
COPY app.py . 
CMD [ "python3", "app.py" ]
