# Copyright 2019 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Tests for `tf.data.Dataset.take_while()`."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import parameterized
import numpy as np

from tensorflow.python.data.kernel_tests import checkpoint_test_base
from tensorflow.python.data.kernel_tests import test_base
from tensorflow.python.data.ops import dataset_ops
from tensorflow.python.framework import combinations
from tensorflow.python.framework import constant_op
from tensorflow.python.framework import errors
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import math_ops
from tensorflow.python.platform import test


class TakeWhileTest(test_base.DatasetTestBase, parameterized.TestCase):

  @combinations.generate(
      combinations.times(
          test_base.default_test_combinations(),
          combinations.combine(num_elements=[14, 15], window_size=[2]) +
          combinations.combine(num_elements=[100], window_size=[3])))
  def testTakeWhileDataset(self, num_elements, window_size):

    def _predicate_func(elem):
      return array_ops.shape(elem)[0] > (window_size - 1)

    dataset = dataset_ops.Dataset.range(num_elements).batch(window_size)
    dataset = dataset.take_while(predicate=_predicate_func).flat_map(
        dataset_ops.Dataset.from_tensor_slices)

    expected_num_elements = int(num_elements / window_size) * window_size
    self.assertDatasetProduces(dataset, np.arange(expected_num_elements))

  @combinations.generate(
      combinations.times(
          test_base.default_test_combinations(),
          combinations.combine(num_elements=[10], upper_bound=[2]) +
          combinations.combine(num_elements=[16], upper_bound=[7]) +
          combinations.combine(num_elements=[100], upper_bound=[99]) +
          combinations.combine(num_elements=[100], upper_bound=[101]) +
          combinations.combine(num_elements=[0], upper_bound=[1])))
  def testTakeWhileDatasetRange(self, num_elements, upper_bound):
    dataset = dataset_ops.Dataset.range(num_elements).take_while(
        lambda x: x < upper_bound)

    self.assertDatasetProduces(dataset,
                               np.arange(min(num_elements, upper_bound)))

  @combinations.generate(test_base.default_test_combinations())
  def testTakeWhileDatasetString(self):

    def not_equal(string):
      return lambda x: math_ops.not_equal(x, constant_op.constant(string))

    string = ["this", "is", "the", "test", "for", "strings"]
    dataset = dataset_ops.Dataset.from_tensor_slices(string).take_while(
        predicate=not_equal("test"))

    next_element = self.getNext(dataset)
    self.assertEqual(b"this", self.evaluate(next_element()))
    self.assertEqual(b"is", self.evaluate(next_element()))
    self.assertEqual(b"the", self.evaluate(next_element()))

    with self.assertRaises(errors.OutOfRangeError):
      self.evaluate(next_element())

  @combinations.generate(
      combinations.times(
          test_base.default_test_combinations(),
          combinations.combine(size=[5], index=[3]) +
          combinations.combine(size=[10], index=[0]) +
          combinations.combine(size=[100], index=[5]) +
          combinations.combine(size=[8], index=[7])))
  def testTakewhileDatasetShortCircuit(self, size, index):

    def _predicate_func(data_elem):
      return data_elem

    boolean_array = [True] * size
    boolean_array[index] = False
    dataset = dataset_ops.Dataset.from_tensor_slices(boolean_array).take_while(
        predicate=_predicate_func)

    next_element = self.getNext(dataset)

    for _ in range(index):
      self.assertTrue(self.evaluate(next_element()))

    with self.assertRaises(errors.OutOfRangeError):
      self.evaluate(next_element())

  @combinations.generate(test_base.default_test_combinations())
  def testTakeWhileDatasetWithRepeat(self):
    dataset = dataset_ops.Dataset.range(10).take_while(
        predicate=lambda x: x < 2).repeat(5)
    self.assertDatasetProduces(dataset, np.tile([0, 1], 5))

  @combinations.generate(test_base.default_test_combinations())
  def testTakeWhileDatasetStops(self):
    dataset = dataset_ops.Dataset.range(10)
    dataset = dataset.take_while(
        lambda x: math_ops.logical_not(math_ops.equal(x, 5)))
    self.assertDatasetProduces(dataset, range(5))


class TakeWhileCheckpointTest(checkpoint_test_base.CheckpointTestBase,
                              parameterized.TestCase):

  def _build_dataset(self, num_elements, upper_bound):
    return dataset_ops.Dataset.range(num_elements).take_while(
        predicate=lambda x: x < upper_bound)

  @combinations.generate(
      combinations.times(
          test_base.default_test_combinations(),
          checkpoint_test_base.default_test_combinations(),
          combinations.combine(num_elements=[10, 23], upper_bound=[10, 23])))
  def test(self, verify_fn, num_elements, upper_bound):
    verify_fn(self, lambda: self._build_dataset(num_elements, upper_bound),
              min(num_elements, upper_bound))


if __name__ == "__main__":
  test.main()
