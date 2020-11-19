# -*- coding: utf-8 -*-
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Index searcher."""

import logging
import os

from dfdewey.datastore.elastic import ElasticsearchDataStore
from dfdewey.datastore.postgresql import PostgresqlDataStore

log = logging.getLogger('dfdewey.index_searcher')


class IndexSearcher():
  """Index Searcher class."""

  def __init__(self, case, image):
    """Create an index searcher."""
    super().__init__()
    self.case = case
    self.elasticsearch = ElasticsearchDataStore()
    self.image = image
    self.images = {}
    self.postgresql = PostgresqlDataStore()

    if image != 'all':
      self.image = os.path.abspath(self.image)
      self._get_image_hash()
    else:
      self._get_case_images()
    print(self.images)

  def _get_case_images(self):
    """Get all images for the case.

    Returns:
      A dictionary of the images in the case.
    """
    images = self.postgresql.query((
        'SELECT image_hash, image_path FROM image_case NATURAL JOIN images '
        'WHERE case_id = \'{0:s}\'').format(self.case))
    for image_hash, image_path in images:
      self.images[image_hash] = image_path

  def _get_image_hash(self):
    """Get an image hash from the datastore.

    Returns:
      MD5 hash for the image stored in PostgreSQL.
    """
    image_hash = self.postgresql.query_single_row(
        'SELECT image_hash FROM images WHERE image_path = \'{0:s}\''.format(
            self.image))
    self.images[image_hash[0]] = self.image
