from __future__ import print_function
import tensorflow as tf
import os

sess = tf.Session()
my_path = os.path.realpath(__file__)

# Model parameters
#W = tf.Variable([.5], dtype=tf.float32)
#b = tf.Variable([-.3], dtype=tf.float32)
# Model input and output
x = tf.placeholder(tf.float32)
#linear_model = W*x + b  # Chosen model. 'linear_model' it is like output.
y = tf.placeholder(tf.float32)

# loss
"""loss = tf.reduce_sum(tf.square(linear_model - y))  # sum of the squares.
tf.summary.scalar("loss", loss)
# optimizer
optimizer = tf.train.GradientDescentOptimizer(0.1)
train = optimizer.minimize(loss)"""

# training data
x_train = [1, 2, 3, 4]
y_train = [0, -1, -2, -3]
tf.summary.scalar('x', x_train)
tf.summary.scalar('y', y_train)

add_node = x - y

# training loop
result = sess.run(add_node, {x: x_train, y: y_train})
print("result=" + str(result))
tf.summary.scalar('result', result)
merged = tf.summary.merge_all()
tf.global_variables_initializer().run()
result = sess.run(merged, {x: x_train, y: y_train})  # reset values to wrong
file_writer = tf.summary.FileWriter(os.path.join(my_path, "..", "instance", "tflogs"), sess.graph)
file_writer.add_summary(result)
"""for i in range(1000):
    tf.summary.scalar("x", x)
    tf.summary.scalar("y", y)
    #tf.summary.scalar("linear_model", linear_model)
    foo = sess.run(train, {x: x_train, y: y_train})
    file_writer.add_summary(foo)

# evaluate training accuracy
curr_W, curr_b, curr_loss = sess.run([W, b, loss], {x: x_train, y: y_train})
print("W: %s b: %s loss: %s" % (curr_W, curr_b, curr_loss))"""

