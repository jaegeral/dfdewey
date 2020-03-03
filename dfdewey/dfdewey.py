# -*- coding: utf-8 -*-
# Copyright 2019 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""DFDewey Command-Line Interface."""

import argparse
import datetime
import os
import subprocess
import tempfile

from datastore.elastic import ElasticsearchDataStore
from datastore.postgresql import PostgresqlDataStore
from utils import image


class _StringRecord(object):

  def __init__(self):
    self.image = ''
    self.offset = 0
    self.file_offset = None
    self.data = ''


def parse_args():
  """Argument parsing function.

  Returns:
      Arguments namespace.
  """
  parser = argparse.ArgumentParser()

  parser.add_argument('-c', '--case', required=True, help='case ID')
  parser.add_argument('-i', '--image', help='image file')

  # Indexing args
  parser.add_argument(
      '--no_base64', help='don\'t decode base64', action='store_true')
  parser.add_argument(
      '--no_gzip', help='don\'t process gzip files', action='store_true')
  parser.add_argument(
      '--no_zip', help='don\'t process zip files', action='store_true')

  # Search args
  parser.add_argument('-s', '--search', help='search query')
  parser.add_argument('--search_list', help='file with search queries')
  # parser.add_argument(
      # '-f', '--file_lookup', help='enable file lookups', action='store_true')

  args = parser.parse_args()
  return args


def process_image(image_file, case, no_base64=None, no_gzip=None, no_zip=None):
  """Image processing function.

  Run string extraction, indexing, and filesystem parsing for image file.

  Args:
      image_file (string):  The image file to be processed
      case (string):        Case ID
      no_base64 (bool):     Don't decode Base64
      no_gzip (bool):       Don't decompress gzip streams
      no_zip (bool):        Don't decompress zip archives
  """
  image_path = os.path.abspath(image_file)
  output_path = tempfile.mkdtemp()

  cmd = ['bulk_extractor',
         '-o', output_path,
         '-x', 'all',
         '-e', 'wordlist']

  if not no_base64:
    cmd.extend(['-e', 'base64'])
  if not no_gzip:
    cmd.extend(['-e', 'gzip'])
  if not no_zip:
    cmd.extend(['-e', 'zip'])

  cmd.extend(['-S', 'strings=YES', '-S', 'word_max=1000000'])
  cmd.extend([image_path])
  print('Processing start: {0!s}'.format(datetime.datetime.now()))
  print('\n*** Running bulk extractor:\n{0:s}'.format(' '.join(cmd)))
  output = subprocess.check_output(cmd)
  md5_offset = output.index(b'MD5') + 19
  image_hash = output[md5_offset:md5_offset+32].decode('utf-8')
  print('String extraction completed: {0!s}'.format(datetime.datetime.now()))
  print('\n*** Parsing image')
  needs_indexing = image.initialise_block_db(image_path, image_hash, case)
  print('Parsing completed: {0!s}'.format(datetime.datetime.now()))
  if needs_indexing:
    print('\n*** Indexing image')
    index_strings(output_path, image_hash)
    print('Indexing completed: {0!s}'.format(datetime.datetime.now()))
  else:
    print('\n*** Image already indexed')
  print('Processing complete!')


def index_strings(output_path, image_hash):
  """ElasticSearch indexing function.

  Args:
      output_path (string): The output directory from bulk_extractor
      image_hash (string):  MD5 of the parsed image
  """
  print('\n*** Indexing data...')
  es = ElasticsearchDataStore()
  index_name = ''.join(('es', image_hash))
  index_name, event_type = es.create_index(index_name=index_name)
  print('Index {0:s} created.'.format(index_name))

  with open('/'.join((output_path, 'wordlist.txt')), 'r') as strings:
    for line in strings:
      if line[0] != '#':
        string_record = _StringRecord()
        string_record.image = image_hash

        line = line.split('\t')
        offset = line[0]
        data = '\t'.join(line[1:])
        if offset.find('-') > 0:
          offset = offset.split('-')
          image_offset = offset[0]
          file_offset = '-'.join(offset[1:])
          string_record.offset = int(image_offset)
          string_record.file_offset = file_offset
        else:
          string_record.offset = int(offset)

        string_record.data = data
        records = index_record(es, index_name, event_type, string_record)
        if records % 10000000 == 0:
          print('Indexed {0:d} records...'.format(records))

  records = es.import_event(index_name, event_type)
  print('\n*** Indexed {0:d} strings.'.format(records))


def index_record(es, index_name, event_type, string_record):
  """Index a single record.

  Args:
      es (Elasticsearch):     Elasticsearch datastore
      index_name (string):    UUID for the index
      event_type (string):    Type of event being processed
      string_record (record): String record to be indexed

  Returns:
      Number of records processed
  """
  json_record = {
      'image': string_record.image,
      'offset': string_record.offset,
      'file_offset': string_record.file_offset,
      'data': string_record.data
  }
  return es.import_event(index_name, event_type, event=json_record)


def search(query, case, image_path=None, query_list=None):
  """Search function.

  Args:
      query (string): The query to run against the index
      case (string): The case to query (if no specific image is provided)
      image_path (string): Path of the source image
      query_list (string): Path to text file containing search terms

  Returns:
      Search results returned
  """
  tracking_db = PostgresqlDataStore()
  images = {}
  if image_path:
    image_path = os.path.abspath(image_path)

    image_hash = tracking_db.query_single_row(
        'SELECT image_hash FROM images WHERE image_path = \'{0:s}\''.format(
            image_path))

    images[image_hash[0]] = image_path
  else:
    print('No image specified, searching all images in case \'{0:s}\''.format(
        case))
    image_hashes = tracking_db.query(
        'SELECT image_hash FROM image_case WHERE case_id = \'{0:s}\''.format(
            case))
    for image_hash in image_hashes:
      image_hash = image_hash[0]
      image_path = tracking_db.query_single_row(
          'SELECT image_path FROM images WHERE image_hash = \'{0:s}\''.format(
              image_hash))

      images[image_hash] = image_path[0]

  for image_hash, image_path in images.items():
    print('\n\nSearching {0:s} ({1:s})'.format(images[image_hash], image_hash))
    index = ''.join(('es', image_hash))
    if query_list:
      with open(query_list, 'r') as search_terms:
        print('\n*** Searching for terms in \'{0:s}\'...'.format(query_list))
        for term in search_terms:
          term = ''.join(('"', term.strip(), '"'))
          results = search_index(index, term)
          if results['hits']['total']['value'] > 0:
            print('{0:s} - {1:d} hits'.format(
                term, results['hits']['total']['value']))
    else:
      print('\n*** Searching for \'{0:s}\'...'.format(query))
      results = search_index(index, query)
      print('Returned {0:d} results:'.format(results['hits']['total']['value']))
      for hit in results['hits']['hits']:
        filename = image.get_filename_from_offset(
            image_path,
            hit['_source']['image'],
            int(hit['_source']['offset']))
        if hit['_source']['file_offset']:
          print('Offset: {0:d}\tFile: {1:s}\tFile offset:{2:s}\t'
                'String: {3:s}'.format(
                    hit['_source']['offset'],
                    filename,
                    hit['_source']['file_offset'],
                    hit['_source']['data'].strip()))
        else:
          print('Offset: {0:d}\tFile: {1:s}\tString: {2:s}'.format(
              hit['_source']['offset'],
              filename,
              hit['_source']['data'].strip()))


def search_index(index_id, search_query):
  """ElasticSearch search function.

  Args:
      index_id (string): The ID of the index to be searched
      search_query (string): The query to run against the index

  Returns:
      Search results returned
  """
  es = ElasticsearchDataStore()
  return es.search(index_id, search_query, size=1000)


def main():
  """Main DFDewey function."""
  args = parse_args()
  if not args.search and not args.search_list:
    process_image(
        args.image, args.case, args.no_base64, args.no_gzip, args.no_zip)
  elif args.search:
    search(args.search, args.case, args.image)
  elif args.search_list:
    search(None, args.case, args.image, args.search_list)


if __name__ == '__main__':
  main()
