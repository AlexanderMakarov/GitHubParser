from __future__ import print_function
import tensorflow as tf
import os

my_path = os.path.realpath(__file__)
logs_path = os.path.join(my_path, "..", "..", "instance", "tflogs")
"""sess = tf.InteractiveSession()
summary_writer = tf.summary.FileWriter(logs_path, sess.graph)
summary_op = tf.summary.text('config/config', tf.convert_to_tensor('asdasdsad'))
another_summary_op = tf.summary.scalar('scalar/data', tf.convert_to_tensor(3.14))
text = sess.run(summary_op)
scalar = sess.run(another_summary_op)
for data in [text, scalar]:
    summary_writer.add_summary(data, 0)
    summary_writer.add_summary(data, 100)
    summary_writer.add_summary(data, 200)
summary_writer.close()
exit(1)"""

sess = tf.Session()

# Model parameters
W = tf.Variable([.3], dtype=tf.float32, name="W")
b = tf.Variable([-.3], dtype=tf.float32, name="b")
# Model input and output
x = tf.placeholder(tf.float32, name="x")
linear_model = W*x + b
y = tf.placeholder(tf.float32, name="y")

# loss
loss = tf.reduce_sum(tf.square(linear_model - y))  # sum of the squares
tf.summary.scalar("loss", loss)
# optimizer
optimizer = tf.train.GradientDescentOptimizer(0.01)
train = optimizer.minimize(loss)

# training data
x_train = [1, 2, 3, 4]
y_train = [0, -1, -2, -3]
# training loop
merged_ops = tf.summary.merge_all()
init = tf.global_variables_initializer()
sess = tf.Session()
writer = tf.summary.FileWriter(logs_path, sess.graph)
sess.run(init)  # reset values to wrong
for i in range(1000):
    feed_dict = {x: x_train, y: y_train}
    train_result = sess.run(train, feed_dict)
    # Do each 10th step.
    if i % 10 == 0:
        summary_str = sess.run(merged_ops, feed_dict)
        writer.add_summary(summary_str, i)


# evaluate training accuracy
curr_W, curr_b, curr_loss = sess.run([W, b, loss], {x: x_train, y: y_train})
print("W: %s b: %s loss: %s" % (curr_W, curr_b, curr_loss))
#tf.summary.scalar("curr_W", curr_W)
#tf.summary.scalar("curr_b", curr_b)
#tf.summary.scalar("curr_loss", curr_loss)
sess.close()
writer.close()
