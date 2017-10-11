# Brain Tumor Classification
# Script for Creating and Loading TFRecords
# Author: Qixun Qu
# Create on: 2017/10/09
# Modify on: 2017/10/11

#     ,,,         ,,,
#   ;"   ';     ;'   ",
#   ;  @.ss$$$$$$s.@  ;
#   `s$$$$$$$$$$$$$$$'
#   $$$$$$$$$$$$$$$$$$
#  $$$$P""Y$$$Y""W$$$$$
#  $$$$  p"$$$"q  $$$$$
#  $$$$  .$$$$$.  $$$$'
#   $$$DaU$$O$$DaU$$$'
#    '$$$$'.^.'$$$$'
#       '&$$$$$&'

'''

Class BTCTFRecords

-1- Write training patches and validating patches with their
    labels into tfrecord files respectively.
    (1) Check whether all cases can be found in labels file;
    (2) Create three empty temporary filts, which are:
        a text file to save cases' names of training set;
        a text file to save cases' names of validating set;
        a jason file to save the number of volumes of
        training set and validating set;
    (3) Generate cases' names of training and validating set
        respectively according to the label file;
    (4) Extract relevant volumes to write TFRecords.

-2- Load batches and labels for training and validating from
    tfrecords.

'''


import os
import json
import numpy as np
from tqdm import *
import pandas as pd
import tensorflow as tf
from btc_settings import *


class BTCTFRecords():

    def __init__(self):
        '''__INIT__

            No steps in initialization.

            Usage examples:
            ---------------
            - Create instance first:
              tfr = BTCTFRecords()
            - Create TFRecords:
              tfr.create_tfrecord(paras, ...)
            - Load TFRecords:
              outputs = tfr.decode_tfrecord(paras, ...)

        '''

        return

    def create_tfrecord(self, input_dir, output_dir, temp_dir, label_file):
        '''CREATE_TFRECORD

            Initialize variables to create tfrecoeds and carry out
            pipline to write tfrecords for training and validating set.

            Inputs:
            -------
            - input_dir: the path of directory where patches are saved in
            - output_dir: the path of directory to write tfrecord files
            - temp_dir: the path of directory to save temporary files
            - label_file: the path of label file

        '''

        # Check whether the input folder is exist
        if not os.path.isdir(input_dir):
            print("Input directory is not exist.")
            raise

        # Check whether the label file is exist
        if not os.path.isfile(label_file):
            print("The label file is not exist.")
            raise

        # Create folder to save outputs
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        # Generate paths for tfrecords
        self.train_tfrecord = os.path.join(output_dir, TFRECORD_TRAIN)
        self.validate_tfrecord = os.path.join(output_dir, TFRECORD_VALIDATE)

        # Obtain serial numbers of cases
        self.case_no = os.listdir(input_dir)

        # Read labels of all cases from label file
        self.labels = pd.read_csv(label_file)

        # Initialize an empty dictionary to keep amount of
        # patches in training and validating set
        self.volumes_num = {}

        # TFRecords creation pipline
        self._check_case_no()
        self._create_temp_files(temp_dir)
        train_set, validate_set = self._generate_cases_set()
        self._write_tfrecord(input_dir, self.train_tfrecord,
                             train_set, TRAIN_MODE)
        self._write_tfrecord(input_dir, self.validate_tfrecord,
                             validate_set, VALIDATE_MODE)

        # Save dictionary into json file
        with open(self.volumes_num_file, "w") as json_file:
            json.dump(self.volumes_num, json_file)

        return

    def _check_case_no(self):
        '''_CHECK_CASE_NO

            If cases cannot be found in label file, the
            process will be stopped.

        '''

        # Put unfound cases into list
        not_found_cases = []
        all_cases_no = self.labels[CASE_NO].values.tolist()
        for cv in self.case_no:
            if cv not in all_cases_no:
                not_found_cases.append(cv)

        # If the list is not empty, quit program
        if len(not_found_cases) != 0:
            print("Cannot find case in label file.")
            raise

        return

    def _create_temp_files(self, temp_dir):
        '''_CREATE_TEMP_FILES

            Create three empty temporary files in given
            temporary folder.

            Input:
            ------
            - temp_dir: the path of directory where temporary
                        files will be saved in

        '''

        # Function to create empty files
        def create_temp_file(path):
            if os.path.isfile(path):
                os.remove(path)
            open(path, "w").close()

        # Create folder to save temporary files
        if not os.path.isdir(temp_dir):
            os.makedirs(temp_dir)

        # A text file to save cases' names of training set
        self.train_set_file = os.path.join(temp_dir, TRAIN_SET_FILE)
        create_temp_file(self.train_set_file)

        # A text file to save cases' names of validating set
        self.validate_set_file = os.path.join(temp_dir, VALIDATE_SET_FILE)
        create_temp_file(self.validate_set_file)

        # A jason file to save the number of volumes of
        # training set and validating set
        self.volumes_num_file = os.path.join(temp_dir, VOLUMES_NUM_FILE)
        create_temp_file(self.volumes_num_file)

        return

    def _generate_cases_set(self):
        '''_GENERATE_CASES_SET

            Generate cases' names for training set and validating set
            according to the label file.

            For each grade group:
            - Compute the number of cases to train or validate.
              Number of cases in training set = all cases * PROPORTION
              Number of cases in validating set = all cases - cases in training set
              PROPORTION can be found in btc_settings.py.
            - Randomle select cases with respect to training and validating.
            - Put cases' names with their grades into list.

            outputs:
            --------
            - train_set: cases' names and their grades in training set
            - validate_set: cases' names and their grades in validating set

        '''

        # Function to write cases list into file
        def save_cases_names(file, cases):
            txt = open(file, "a")
            for case in cases:
                txt.write(case[0] + CASES_FILE_SPLIT)

        # Initialize empty list for training and validating set
        train_set, validate_set = [], []

        # Generates set for each grade group
        for grade in GRADES_LIST:
            # Get all cases' names of a certain grade
            cases = self.labels[CASE_NO][self.labels[GRADE_LABEL] == grade].values.tolist()

            # Compute number of cases in training set
            cases_num = len(cases)
            train_num = int(cases_num * PROPORTION)

            # Randomly get cases' names for training
            index = list(np.arange(cases_num))
            np.random.seed(RANDOM_SEED)
            train_index = list(np.random.choice(cases_num, train_num, replace=False))

            # Other cases are regarded as validating set
            validate_index = [i for i in index if i not in train_index]

            # Put cases' names with grades into list
            train_set += [[cases[i], grade] for i in train_index]
            validate_set += [[cases[i], grade] for i in validate_index]

        # Save list into file
        save_cases_names(self.train_set_file, train_set)
        save_cases_names(self.validate_set_file, validate_set)

        return train_set, validate_set

    def _write_tfrecord(self, input_dir, tfrecord_path, cases, mode):
        '''_WRITE_TFRECORD

            Write volumes into tfrecord file.
            For each case in training or validating set:
                For each volume in a certain case:
                    Mormalize the volume
                    Write the volume into tfrecord file

            Inputs:
            -------
            - input_dir: the path of directory where keeps all volumes
            - tfrecord_path: the path to save tfrecord file
            - cases: a list consists of cases' names, such as:
                     [["case1", grade_of_case1], ["case2", grade_of_case2]]
            - mode: a symbol to describe the process, "train" or "validate"

        '''

        # normalize the volume
        def normalize(volume):
            return (volume - np.min(volume)) / np.std(volume)

        print("Create TFRecord to " + mode)

        # Variable to count number in training or validating set
        volume_num = 0

        # Create writer
        writer = tf.python_io.TFRecordWriter(tfrecord_path)

        # For each case in list
        for case in tqdm(cases):
            # Generate paths for all volume in one case
            case_path = os.path.join(input_dir, case[0])
            volumes_path = [os.path.join(case_path, p) for p in os.listdir(case_path)]

            for vp in volumes_path:

                # If the volume can not be found, skip to next iteration
                if not os.path.isfile(vp):
                    continue

                # Read, normalize and convert volume
                volume = np.load(vp)
                volume = normalize(volume)
                volume_raw = volume.tobytes()

                # Form an example of a volume with its grade
                example = tf.train.Example(features=tf.train.Features(feature={
                    "label": tf.train.Feature(int64_list=tf.train.Int64List(value=[case[1]])),
                    "volume": tf.train.Feature(bytes_list=tf.train.BytesList(value=[volume_raw]))
                }))

                # Write the example into tfrecord file
                writer.write(example.SerializeToString())

                # Count
                volume_num += 1

        # Close writer
        writer.close()

        # Save number of volume into dictionary
        # {mode1: xxxx, mode2: xxxx}
        self.volumes_num[mode] = volume_num

        return

    def decode_tfrecord(self, path, batch_size,
                        num_epoches, patch_shape,
                        capacity, min_after_dequeue):
        '''DECODE_TFRECORD

            Decode batches from tfrecords according to given settings.
            Global settings can be found in btc_settings.py.

            Inputs:
            -------
            - path: the path of tfrecord file
            - batch_size: the number of volumes in one batch
            - num_epoches: the number of training epoches
            - patch_shape: the shape of each volume
            - capacity: the maximum number of elements in the queue
            - min_after_dequeue: minimum number elements in the queue after
                                 a dequeue, used to ensure a level of mixing
                                 of elements

            Outputs:
            --------
            - volumes: shuffled volumes set for training or validating
            - labels: grade labels for volumes

        '''

        # Set default value of number of epoches
        if not num_epoches:
            num_epoches = None

        with tf.name_scope("input"):
            # Generate queue and load example
            queue = tf.train.string_input_producer([path], num_epochs=num_epoches)
            volume, label = self._decode_example(queue, patch_shape)

            # Shuffle volumes
            volumes, labels = tf.train.shuffle_batch([volume, label],
                                                     batch_size=batch_size,
                                                     num_threads=NUM_THREADS,
                                                     capacity=capacity,
                                                     min_after_dequeue=min_after_dequeue)
        return volumes, labels

    def _decode_example(self, queue, patch_shape):
        '''_DECORD_EXAMPLE

            Decode one example from tfrecord file,
            including its volume and label.

            Inputs:
            -------
            - queue: a queue of input filenames
            - patch_shape: shape of one volume

            Outputs:
            --------
            - volume: one volume in given shape
            - label: the grade of the volume

        '''

        # Load features for one example, in this case,
        # they are volume and its label
        reader = tf.TFRecordReader()
        _, serialized_example = reader.read(queue)
        features = tf.parse_single_example(
            serialized_example,
            features={
                "label": tf.FixedLenFeature([], tf.int64),
                "volume": tf.FixedLenFeature([], tf.string)
            })

        # Load and reshape volume
        volume = tf.decode_raw(features["volume"], tf.float32)
        volume = tf.reshape(volume, patch_shape)

        # Extract its label
        label = tf.cast(features["label"], tf.uint8)

        return volume, label


if __name__ == "__main__":

    parent_dir = os.path.dirname(os.getcwd())

    input_dir = os.path.join(parent_dir, DATA_FOLDER, AUGMENT_FOLDER)
    output_dir = os.path.join(parent_dir, DATA_FOLDER, TFRECORDS_FOLDER)
    temp_dir = os.path.join(TEMP_FOLDER, TFRECORDS_FOLDER)
    label_file = os.path.join(parent_dir, DATA_FOLDER, LABEL_FILE)

    tfr = BTCTFRecords()
    tfr.create_tfrecord(input_dir, output_dir, temp_dir, label_file)