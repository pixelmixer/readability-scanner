
import os
import json
import hug
import tarfile
import requests
import logging

from datetime import datetime, timezone
import time

from pymongo import MongoClient
from bson import json_util
import pandas as pd

# Set up OpenTelemetry logging for Hug API
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Set up OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter for traces
otlp_exporter = OTLPSpanExporter(
    endpoint="http://host.docker.internal:30007",
    insecure=True
)

# Add span processor
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Set up OpenTelemetry logging
LoggingInstrumentor().instrument()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# For local streaming, the websockets are hosted without ssl - http://
HOST = '192.168.86.32:5000'
URI = f'http://{HOST}/api/v1/generate'

# Requires the PyMongo package.
# https://api.mongodb.com/python/current

client = MongoClient(
    'mongodb://readability-database:27017/?readPreference=primary&appname=MongoDB%20Compass%20Community&ssl=false')
db = client["readability-database"]
collection = db["documents"]


@hug.get('/kaggle')
def kaggle():
    # kaggle datasets download -d pixelmixer/political-news-031121-to-080221
    return "Kaggle??"


@hug.get('/happy_birthday')
def happy_birthday(name, age: hug.types.number = 1):
    """Says happy birthday to a user"""
    return "Happy {age} Birthday {name}!".format(**locals())


def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))
        return tar


@hug.get('/get_zip', output=hug.output_format.file)
def get_zip():
    return './data.tar.gz'


@hug.get('/create_zip', output=hug.output_format.file)
def create_zip():
    """Creates and returns a zip file of the test contents"""
    tar = make_tarfile('data.tar.gz', './data/')

    print("Loaded tar")
    print(tar.getmembers())

    return './data.tar.gz'


@hug.get('/generate_files', output=hug.output_format.html)
def generate_files():
    """Generates training and test files"""
    filters = {}
    project = {
        'Smog': True,
        'Flesch': True,
        'Gunning Fog': True,
        'Spache': True,
        'Automated Readability': True,
        'paragraphs': True,
        'words': True,
        'sentences': True
    }
    # result = collection.find(filters, project)

    result = collection.aggregate([
        {
            '$match': {
                'origin': {
                    '$ne': None
                }
            }
        }, {
            '$lookup': {
                'from': 'urls',
                'localField': 'origin',
                'foreignField': 'url',
                'as': 'host'
            }
        }, {
            '$replaceRoot': {
                'newRoot': {
                    '$mergeObjects': [
                        {
                            '$arrayElemAt': [
                                '$host', 0
                            ]
                        }, '$$ROOT'
                    ]
                }
            }
        }, {
            '$project': {
                'reliability': 1,
                'Host': 1,
                'Flesch': 1,
                'Automated Readability': 1,
                'Smog': 1,
                'Spache': 1,
                'gunning fog': 1
            }
        }
    ])

    df = pd.DataFrame.from_records(result)

    print(df.describe())

    return df.describe().to_html()

    document_list = [doc for doc in result]
    # existing_test_file_count = len(os.listdir("data/test"))
    # indexes = {}

    # TODO: Avoid duplicating documents and don't add documents with the same content twice....
    # for i, doc in enumerate(document_list):
    #     path = doc['Host']

    #     train_dir_path = "data/train/{0}".format(path, i)
    #     indexes[path] =
    print(f"Evaluating {len(document_list)} train and test documents")
    skipped = 0

    tic = time.perf_counter()

    for i, doc in enumerate(document_list):
        path = doc['reliability']
        content = doc['Cleaned Data']

        train_path = f"data/train/{path}/"

        if not os.path.exists(train_path):
            os.mkdir(train_path)

        train_file_name = f"{i}.txt"
        train_file_path = f"{train_path}{train_file_name}"

        if not os.path.isfile(train_file_path):
            train_file = open(train_file_path, "wt")
            train_bytes_written = train_file.write(content)
            train_file.close()

            print(f"Wrote {train_bytes_written} bytes to {train_file_path}.")
        else:
            skipped += 1
            # print(f"{train_file_path} exists, skipping.")

        test_path = f"data/test/{path}/"

        if not os.path.exists(test_path):
            os.mkdir(test_path)

        test_file_name = f"{i}.txt"
        test_file_path = f"{test_path}{test_file_name}"

        if not os.path.isfile(test_file_path):
            test_file = open(test_file_path, "wt")
            test_bytes_written = test_file.write(content)
            test_file.close()

            print(f"Wrote {test_bytes_written} bytes to {test_file_path}.")
        else:
            skipped += 1
            # print(f"{test_file_path} exists, skipping.")

    # res = json.dumps([doc for doc in result], default=json_util.default)

    toc = time.perf_counter()

    # TODO:
    # [x] Read json data
    # [ ] Save each line to corresponding directory with Host.
    if skipped > 0:
        return f"Wrote {(len(document_list)*2) - skipped} and skipped {skipped} documents in {toc - tic:0.4f} seconds"
    else:
        return f"Wrote {len(document_list)*2} documents in {toc - tic:0.4f} seconds"


@hug.get('/export')
def export():
    print('getting export')
    result = collection.aggregate([
        {
            '$match': {
                'publication_date': {
                    '$gte': datetime(2021, 3, 29, 4, 0, 0, tzinfo=timezone.utc),
                    '$lte': datetime(2021, 4, 5, 3, 59, 59, tzinfo=timezone.utc)
                },
                'origin': {
                    '$ne': None
                }
            }
        }, {
            '$project': {
                'url': '$url',
                'Host': '$Host'
            }
        }
    ])
    # print(result)
    print(list(result))

    return result

@hug.get('/wordcloud')
def word_cloud():
    print('Collecting Words')
    result = collection.aggregate([
        {
            '$project': {
                'words': {
                    '$split': [
                        '$Cleaned Data', ' '
                    ]
                }
            }
        }, {
            '$unwind': {
                'path': '$words'
            }
        }, {
            '$group': {
                '_id': '$words',
                'count': {
                    '$sum': 1
                }
            }
        }, {
            '$sort': {
                'count': -1
            }
        }, {
            '$match': {
                'count': {
                    '$gt': 1
                }
            }
        }, {
            '$limit': 5
        }
    ])
    return result



@hug.post('/summarize')
def summarize(prompt, history = {'internal': [], 'visible': []}):
    request = {
        'prompt': f'{prompt}',
        'max_new_tokens': 250,
        'auto_max_new_tokens': False,
        'max_tokens_second': 0,
        'history': history,
        'mode': 'instruct',  # Valid options: 'chat', 'chat-instruct', 'instruct'
        'character': 'Example',
        'instruction_template': 'Vicuna-v1.1',  # Will get autodetected if unset
        'your_name': 'You',
        # 'name1': 'name of user', # Optional
        # 'name2': 'name of character', # Optional
        # 'context': 'character context', # Optional
        # 'greeting': 'greeting', # Optional
        # 'name1_instruct': 'You', # Optional
        # 'name2_instruct': 'Assistant', # Optional
        # 'context_instruct': 'context_instruct', # Optional
        # 'turn_template': 'turn_template', # Optional
        'regenerate': False,
        '_continue': False,
        'chat_instruct_command': 'Continue the chat dialogue below. Write a single reply for the character. Summarize the following text: "<|character|>".\n\n<|prompt|>',

        # Generation params. If 'preset' is set to different than 'None', the values
        # in presets/preset-name.yaml are used instead of the individual numbers.
        'preset': 'None',
        'do_sample': True,
        'temperature': 0.7,
        'top_p': 0.1,
        'typical_p': 1,
        'epsilon_cutoff': 0,  # In units of 1e-4
        'eta_cutoff': 0,  # In units of 1e-4
        'tfs': 1,
        'top_a': 0,
        'repetition_penalty': 1.18,
        'repetition_penalty_range': 0,
        'top_k': 40,
        'min_length': 0,
        'no_repeat_ngram_size': 0,
        'num_beams': 1,
        'penalty_alpha': 0,
        'length_penalty': 1,
        'early_stopping': False,
        'mirostat_mode': 0,
        'mirostat_tau': 5,
        'mirostat_eta': 0.1,
        'grammar_string': '',
        'guidance_scale': 1,
        'negative_prompt': '',

        'seed': -1,
        'add_bos_token': True,
        'truncation_length': 2048,
        'ban_eos_token': False,
        'custom_token_bans': '',
        'skip_special_tokens': True,
        'stopping_strings': []
    }

    response = requests.post(URI, json=request)

    if response.status_code == 200:
        print(response.json())
        # result = response.json()['results'][0]['text']
        # print(prompt + result)
        return response.json()

    return prompt