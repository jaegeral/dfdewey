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

from utils import image


def main():
  filename = image.get_filename_from_offset(
      '/usr/local/google/home/jasonsolomon/Downloads/images/greendale/'
      'images_studentpc10.dd',
      355)
  print(filename)
  print('===')
  filename = image.get_filename_from_offset(
      '/usr/local/google/home/jasonsolomon/Downloads/images/greendale/'
      'images_studentpc10.dd',
      5448488236)
  print(filename)
  print('===')
  filename = image.get_filename_from_offset(
      '/usr/local/google/home/jasonsolomon/Downloads/images/greendale/'
      'images_acserver.dd',
      365965982)
  print(filename)
  print('===')


if __name__ == '__main__':
  main()
