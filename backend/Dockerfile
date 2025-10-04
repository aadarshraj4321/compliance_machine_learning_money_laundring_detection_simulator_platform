FROM python:3.11-slim

WORKDIR /code/src

COPY ./requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /tmp/requirements.txt

# We now explicitly copy the source files
COPY ./src .

# The CMD remains the same
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]