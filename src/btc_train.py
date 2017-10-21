# Brain Tumor Classification
# Script for Training Models
# Author: Qixun Qu
# Create on: 2017/10/14
# Modify on: 2017/10/21

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

Class BTCTrain

-1- Models are defined in class BTCModels.
-2- Hyper-parameters can be set in btc_parameters.py.
-3- Loading tfrecords for training and validating by
    functions in class BTCTFRecords.

'''


import os
import shutil
import numpy as np
import tensorflow as tf
from btc_settings import *
from btc_models import BTCModels
from btc_parameters import parameters
from btc_tfrecords import BTCTFRecords


class BTCTrain():

    def __init__(self, net, paras, save_path, logs_path):
        '''__INIT__

            Initialization of class BTCTrain to set parameters
            for constructing, training and validating models.

            Inputs:
            -------
            - net: string, the name of the model applied to train
            - paras: dict, parameters for training the model, defined
                     in btc_parameters.py
            - save_path: string, the path of the folder to save models
            - logs_path: string, the path of the folder to save logs

        '''

        self.net = net

        # Initialize BTCTFRecords to load data
        self.tfr = BTCTFRecords()

        # Create folders to keep models
        # if the folder is not exist
        self.model_path = os.path.join(save_path, net)
        if not os.path.isdir(self.model_path):
            os.makedirs(self.model_path)

        # Create folders to keep models
        # if the folder is not exist
        self.logs_path = os.path.join(logs_path, net)
        if os.path.isdir(self.logs_path):
            shutil.rmtree(self.logs_path)
        os.makedirs(self.logs_path)

        # Basic settings
        self.train_path = paras["train_path"]
        self.validate_path = paras["validate_path"]
        self.classes_num = paras["classes_num"]
        self.patch_shape = paras["patch_shape"]
        self.capacity = paras["capacity"]
        self.min_after_dequeue = paras["min_after_dequeue"]

        # For training process
        self.batch_size = paras["batch_size"]
        self.num_epoches = paras["num_epoches"]
        self.drop_rate = paras["drop_rate"]

        # For models' structure
        self.act = paras["activation"]
        self.alpha = paras["alpha"]
        self.bn_momentum = paras["bn_momentum"]
        self.drop_rate = paras["drop_rate"]

        # Initialize BTCModels to set general settings
        self.models = BTCModels(self.net, self.classes_num,
                                self.act, self.alpha,
                                self.bn_momentum, self.drop_rate)

        # Computer the number of batches in each epoch for
        # both training and validating respectively
        self.tepoch_iters = self._get_epoch_iters(paras["train_num"])
        self.vepoch_iters = self._get_epoch_iters(paras["validate_num"])

        return

    def _get_epoch_iters(self, num):
        '''_GET_EPOCH_ITERS

            The helper funtion to compute the number of iterations
            of each epoch.

            Input:
            -------
            - num: int, the number of patches in dataset

            Output:
            -------
            - a list consists of iterations in each epoch

        '''

        index = np.arange(1, self.num_epoches + 1)
        iters_per_epoch = np.floor(index * (num / self.batch_size))

        return iters_per_epoch.astype(np.int64)

    def _load_data(self, tfrecord_path):
        '''_LOAD_DATA

            The helper funtion to load patches from tfrecord files.
            All patches are suffled abd returned in batch size.

            Input:
            ------
            - tfrecord_path: the path fo tfrecord file

            Output:
            -------
            - suffled patches in batch size

        '''

        return self.tfr.decode_tfrecord(path=tfrecord_path,
                                        batch_size=self.batch_size,
                                        num_epoches=self.num_epoches,
                                        patch_shape=self.patch_shape,
                                        capacity=self.capacity,
                                        min_after_dequeue=self.min_after_dequeue)

    def train(self):
        '''TRAIN

            Train and validate the choosen model.

        '''

        # Define inputs for model:
        # - features: 5D volume, shape in [batch_size, height, width, depth, channels]
        # - labels: 1D list, shape in [batch_size]
        # - training symbol: boolean
        with tf.name_scope("inputs"):
            x = tf.placeholder(tf.float32, [None] + self.patch_shape)
            y_input_classes = tf.placeholder(tf.int64, [None])
            is_training = tf.placeholder(tf.bool)

        # Set models by given variable
        if self.net == CNN:
            network = self.models.cnn
        elif self.net == FULL_CNN:
            network = self.models.full_cnn
        elif self.net == RES_CNN:
            network = self.models.res_cnn
        elif self.net == DENSE_CNN:
            network = self.models.dense_cnn
        else:  # Raise error if model cannot be found
            raise ValueError("Could not found model.")

        # Obtain logits from the model
        y_output_logits = network(x, is_training)

        # Compute loss
        with tf.name_scope("loss"):
            # Convert labels to onehot array first, such as:
            # [0, 1, 2] ==> [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
            y_input_onehot = tf.one_hot(indices=y_input_classes, depth=self.classes_num)
            loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(labels=y_input_onehot,
                                                                          logits=y_output_logits))
        # Add loss into summary
        tf.summary.scalar("loss", loss)

        # Compute accuracy
        with tf.name_scope("accuracy"):
            # Obtain the predicted labels for each input example first
            y_output_classes = tf.argmax(input=y_output_logits, axis=1)
            correction_prediction = tf.equal(y_output_classes, y_input_classes)
            accuracy = tf.reduce_mean(tf.cast(correction_prediction, tf.float32))

        # Add accuracy into summary
        tf.summary.scalar("accuracy", accuracy)

        # Merge summary
        # The summary can be displayed by TensorBoard
        merged = tf.summary.merge_all()

        # Optimize loss
        with tf.name_scope("train"):
            # Update moving_mean and moving_variance of
            # batch normalization in training process
            update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
            with tf.control_dependencies(update_ops):
                train_op = tf.train.AdamOptimizer(1e-2).minimize(loss)

        # Load data from tfrecord files
        with tf.name_scope("tfrecords"):
            tra_volumes, tra_labels = self._load_data(self.train_path)
            val_volumes, val_labels = self._load_data(self.validate_path)

        # Create a saver to save model while training
        saver = tf.train.Saver()

        # Define initialization of graph
        with tf.name_scope("init"):
            init = tf.group(tf.local_variables_initializer(),
                            tf.global_variables_initializer())

        sess = tf.InteractiveSession()

        # Create writers to write logs in file
        tra_writer = tf.summary.FileWriter(os.path.join(self.logs_path, "train"), sess.graph)
        val_writer = tf.summary.FileWriter(os.path.join(self.logs_path, "validate"), sess.graph)

        sess.run(init)

        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(sess=sess, coord=coord)

        tra_iters, one_tra_iters, val_iters, epoch_no = 0, 0, 0, 0

        print((PCB + "Training and Validating model: {}\n" + PCW).format(self.net))

        # Lists to save loss and accuracy of each training step
        tloss_list, taccuracy_list = [], []

        try:
            while not coord.should_stop():
                # Training step
                # Feed the graph, run optimizer and get metrics
                tx, ty = sess.run([tra_volumes, tra_labels])
                tra_fd = {x: tx, y_input_classes: ty, is_training: True}
                tsummary, tloss, taccuracy, _ = sess.run([merged, loss, accuracy,
                                                         train_op], feed_dict=tra_fd)

                tra_iters += 1
                one_tra_iters += 1

                # Record metrics of training steps
                tloss_list.append(tloss)
                taccuracy_list.append(taccuracy)
                tra_writer.add_summary(tsummary, tra_iters)

                print((PCG + "[Epoch {}] ").format(epoch_no + 1),
                      "Train Step {}: ".format(one_tra_iters),
                      "Loss: {0:.10f}, ".format(tloss),
                      ("Accuracy: {0:.10f}" + PCW).format(taccuracy))

                if tra_iters % self.tepoch_iters[epoch_no] == 0:
                    # Validating step
                    # Lists to save loss and accuracy of each validating step
                    vloss_list, vaccuracy_list = [], []
                    while val_iters < self.vepoch_iters[epoch_no]:
                        val_iters += 1
                        # Feed the graph, get metrics
                        vx, vy = sess.run([val_volumes, val_labels])
                        val_fd = {x: vx, y_input_classes: vy, is_training: False}
                        vsummary, vloss, vaccuracy = sess.run([merged, loss, accuracy],
                                                              feed_dict=val_fd)

                        # Record metrics of validating steps
                        vloss_list.append(vloss)
                        vaccuracy_list.append(vaccuracy)
                        val_writer.add_summary(vsummary, tra_iters)

                    # Compute mean loss and mean accuracy of training steps
                    # in one epoch, and empty lists for next epoch
                    tloss_mean = np.mean(tloss_list)
                    taccuracy_mean = np.mean(taccuracy_list)
                    tloss_list, taccuracy_list = [], []

                    print((PCY + "[Epoch {}] ").format(epoch_no + 1),
                          "Train Stage: ",
                          "Mean Loss: {0:.10f}, ".format(tloss_mean),
                          ("Mean Accuracy: {0:.10f}" + PCW).format(taccuracy_mean))

                    # Compute mean loss and mean accuracy of validating steps in one epoch
                    vloss_mean = np.mean(vloss_list)
                    vaccuracy_mean = np.mean(vaccuracy_list)

                    print((PCY + "[Epoch {}] ").format(epoch_no + 1),
                          "Validate Stage: ",
                          "Mean Loss: {0:.10f}, ".format(vloss_mean),
                          ("Mean Accuracy: {0:.10f}" + PCW).format(vaccuracy_mean))

                    # Create folder to save model
                    ckpt_dir = os.path.join(self.model_path, "epoch-" + str(epoch_no + 1))
                    if os.path.isdir(ckpt_dir):
                        shutil.rmtree(ckpt_dir)
                    os.makedirs(ckpt_dir)

                    # Save model's graph and variables of each epoch into folder
                    save_path = os.path.join(ckpt_dir, self.net)
                    saver.save(sess, save_path, global_step=epoch_no + 1)
                    print((PCC + "[Epoch {}] ").format(epoch_no + 1),
                          ("Model was saved in: {}\n" + PCW).format(ckpt_dir))

                    one_tra_iters = 0
                    epoch_no += 1

        except tf.errors.OutOfRangeError:
            # Stop training
            print(PCB + "Training has stopped." + PCW)
            print((PCB + "Logs have been saved in: {}" + PCW).format(self.logs_path))
        finally:
            coord.request_stop()

        coord.join(threads)
        sess.close()

        return


if __name__ == "__main__":

    parent_dir = os.path.dirname(os.getcwd())
    save_path = os.path.join(parent_dir, "models")
    logs_path = os.path.join(parent_dir, "logs")

    model = CNN
    # model = FULL_CNN
    # model = RES_CNN
    # model = DENSE_CNN

    btc = BTCTrain(model, parameters, save_path, logs_path)
    btc.train()
