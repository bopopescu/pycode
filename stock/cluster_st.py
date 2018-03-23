import numpy as np
import theano
import theano.tensor as T
from theano import function, config, shared, sandbox
#from theano import ProfileMode
import warnings

warnings.filterwarnings("ignore")

# set path=d:\dev\Anaconda3\Scripts;d:\dev\Anaconda3;C:\WINDOWS\system32;C:\WINDOWS;C:\WINDOWS\System32\Wbem;D:\dev\sbt\bin;e:\devtool\winutil\bin
# set QT_PLUGIN_PATH=d:\dev\Anaconda3\Library\plugins  matplotlib failed, need this

# Dummy Data
# https://github.com/erogol/KLP_KMEANS/blob/master/klp_kmeans.py

def create_dummy_data(N=4000, feats=784):
    rng = np.random
    DATA = rng.randn(N, feats)
    DATA = np.random.randn(N, feats)
    return DATA


def klp_kmeans(data, cluster_num, alpha, epochs=-1, batch=1, verbose=False, use_gpu=False):
    '''
        Theano based implementation, likely to use GPU as well with required Theano
        configurations. Refer to http://deeplearning.net/software/theano/tutorial/using_gpu.html
        for GPU settings
        Inputs:
            data - [instances x variables] matrix of the data.
            cluster_num - number of requisite clusters
            alpha - learning rate
            epoch - how many epoch you want to go on clustering. If not given, it is set with
                Kohonen's suggestion 500 * #instances
            batch - batch size. Larger batch size is better for Theano and GPU utilization
            verbose - True if you want to verbose the algorithm's iterations
        Output:
            W - final cluster centroids
    '''
    if use_gpu:
        config.floatX = 'float32'  # Theano needs this type of data for GPU use

    warnings.simplefilter("ignore", DeprecationWarning)
    warnings.filterwarnings("ignore")

    rng = np.random
    # From Kohonen's paper
    if epochs == -1:
        print (data.shape[0])
        epochs = 500 * data.shape[0]

    if use_gpu == False:
        # Symmbol variables
        X = T.dmatrix('X')
        WIN = T.dmatrix('WIN')

        # Init weights random
        W = theano.shared(rng.randn(cluster_num, data.shape[1]), name="W")
    else:
        # for GPU use
        X = T.matrix('X')
        WIN = T.matrix('WIN')
        W = theano.shared(rng.randn(cluster_num, data.shape[1]).astype(theano.config.floatX), name="W")

    W_old = W.get_value()

    # Find winner unit
    bmu = ((W ** 2).sum(axis=1, keepdims=True) + (X ** 2).sum(axis=1, keepdims=True).T - 2 * T.dot(W, X.T)).argmin(
        axis=0)
    dist = T.dot(WIN.T, X) - WIN.sum(0)[:, None] * W
    err = abs(dist).sum() / X.shape[0]

    update = function([X, WIN], outputs=err, updates=[(W, W + alpha * dist)], allow_input_downcast=True)
    find_bmu = function([X], bmu, allow_input_downcast=True)

    if any([x.op.__class__.__name__ in ['Gemv', 'CGemv', 'Gemm', 'CGemm'] for x in
            update.maker.fgraph.toposort()]):
        print( 'Used the cpu' )
    elif any([x.op.__class__.__name__ in ['GpuGemm', 'GpuGemv'] for x in
              update.maker.fgraph.toposort()]):
        print ('Used the gpu')
    else:
        print ('ERROR, not able to tell if theano used the cpu or the gpu')
        print (update.maker.fgraph.toposort())

    # Update
    for epoch in range(epochs):
        C = 0
        for i in range(0, data.shape[0], batch):
            batch_data = data[i:i + batch, :]
            D = find_bmu(batch_data)
            # for GPU use
            if use_gpu:
                S = np.zeros([batch, cluster_num], config.floatX)
            else:
                S = np.zeros([batch_data.shape[0], cluster_num])
            S[:, D] = 1
            cost = update(batch_data, S)

        if epoch % 10 == 0 and verbose:
            print ("Avg. centroid distance -- ", cost.sum(), "\t EPOCH : ", epoch)
    return W.get_value()


def kmeans(X, cluster_num, numepochs, learningrate=0.01, batchsize=100, verbose=True):
    '''
        klp_kmeans based NUMPY, better for small scale problems
        inherited from http://www.iro.umontreal.ca/~memisevr/code.html
    '''

    rng = np.random
    W = rng.randn(cluster_num, X.shape[1])
    X2 = (X ** 2).sum(1)[:, None]
    for epoch in range(numepochs):
        for i in range(0, X.shape[0], batchsize):
            D = -2 * np.dot(W, X[i:i + batchsize, :].T) + (W ** 2).sum(1)[:, None] + X2[i:i + batchsize].T
            S = (D == D.min(0)[None, :]).astype("float").T
            W += learningrate * (np.dot(S.T, X[i:i + batchsize, :]) - S.sum(0)[:, None] * W)
        if verbose:
            print ("epoch", epoch, "of", numepochs, " cost: ", D.min(0).sum())
    return W


'''
DEMO CODES
	You might choose the implementation based on the following demo results
	It decomposed to 3 basic measure of quality
		As increasing - EPOCHS - CLUSTER_SIZE - Data
	and code plots the results.
'''
if __name__ == '__main__':
    from sklearn import cluster, datasets
    import matplotlib.pyplot as plt
    import time

    import sys, numpy as np
    sys.path.insert(0, 'e:/worksrc/pycode/stock')
    import cluster_st as c

    dd = np.loadtxt('e:/stock/xx', float)
    W = c.klp_kmeans(dd, 20, alpha=0.001, epochs=1000, batch=10, verbose=True)
    W.tofile('a.bin')
    for i in range(dd.shape[1]): print(np.max(dd[:, i]), np.min(dd[:,i]))
    for i in range(W.shape[1]): print(np.max(W[:, i]), np.min(W[:, i]))
    for i in range(W.shape[0]): plt.plot(W[i, :])
    W = np.fromfile('a.bin').reshape(20,30)


    dd = np.random.randn(4000, 30)
    import __file__ as c
    W2 = c.kmeans(dd, 100, numepochs=100, batchsize=10, learningrate=0.001, verbose=False)

    # Epoch Comparison
    # print 'Epoch length Comparison ----'
    # blobs = datasets.make_blobs(n_samples=4000, random_state=8)
    # noisy_moons = datasets.make_moons(n_samples=4000, noise=.05)
    # noisy_circles = datasets.make_circles(n_samples=2000, factor=.5, noise=.05)
    # DATA = noisy_circles[0].astype(theano.config.floatX)

    # klp_kmeans_times = []
    # klp_kmeans_times_gpu = []
    # kmeans_times = []
    # for i in range(10, 1000, 20):
    #     t1 = time.time()
    #     W = klp_kmeans(DATA ,1000,alpha = 0.001, epochs=i, batch=10, verbose=False)
    #     t2 = time.time()

    #     t5 = time.time()
    #     W3 = klp_kmeans(DATA ,1000,alpha = 0.001, epochs=i, batch=10, verbose=False, use_gpu=True)
    #     t6 = time.time()

    #     t3 = time.time()
    #     W2 = kmeans(DATA,1000, numepochs = i, batchsize=10, learningrate=0.001, verbose=False)
    #     t4 = time.time()

    #     klp_kmeans_times.append(t2-t1)
    #     klp_kmeans_times_gpu.append(t6-t5)
    #     kmeans_times.append(t4-t3)

    # plt.scatter(DATA[:,0], DATA[:,1], color='red')
    # plt.scatter(W[:,0],W[:,1],color='blue',s=20,edgecolor='none')
    # plt.scatter(W3[:,0],W3[:,1],color='green',s=20,edgecolor='none')
    # plt.scatter(W2[:,0],W2[:,1],color='yellow',s=20,edgecolor='none')

    # plt.scatter(10+(arange(len(klp_kmeans_times))*20), klp_kmeans_times, color='blue')
    # plt.scatter(10+(arange(len(klp_kmeans_times_gpu))*20), klp_kmeans_times_gpu, color='green')
    # plt.scatter(10+(arange(len(kmeans_times))*20), kmeans_times, color='yellow')

    # Cluster size test

    print ('Cluster number comparison ----')
    blobs = datasets.make_blobs(n_samples=4000, random_state=8)
    noisy_moons = datasets.make_moons(n_samples=4000, noise=.05)
    noisy_circles = datasets.make_circles(n_samples=2000, factor=.5,
                                          noise=.05)
    DATA = noisy_circles[0]
    klp_kmeans_times2 = []
    klp_kmeans_times2_gpu = []
    kmeans_times2 = []
    for i in range(10, 1000, 20):
        t1 = time.time()
        W = klp_kmeans(DATA, i, alpha=0.001, epochs=1000, batch=10, verbose=False)
        t2 = time.time()

        t5 = time.time()
        W3 = klp_kmeans(DATA, i, alpha=0.001, epochs=1000, batch=10, verbose=False, use_gpu=True)
        t6 = time.time()

        t3 = time.time()
        W2 = kmeans(DATA, i, numepochs=1000, batchsize=10, learningrate=0.001, verbose=False)
        t4 = time.time()

        klp_kmeans_times2.append(t2 - t1)
        klp_kmeans_times2_gpu.append(t6 - t5)
        kmeans_times2.append(t4 - t3)

    plt.title('Cluster Num vs Time')
    plt.xlabel('Num Clusters')
    plt.ylabel('time')
    plt.plot(range(10, 1000, 20), klp_kmeans_times2, '-o', color='blue')
    plt.show()
    plt.plot(range(10, 1000, 20), klp_kmeans_times2_gpu, '-o', color='green')
    plt.show()
    plt.plot(range(10, 1000, 20), kmeans_times2, '-o', color='yellow')
    plt.show()

    # DATA size test
    print ('DATA size comparison ----')
    blobs = datasets.make_blobs(n_samples=4000, random_state=8)
    noisy_moons = datasets.make_moons(n_samples=4000, noise=.05)
    noisy_circles = datasets.make_circles(n_samples=2000, factor=.5,
                                          noise=.05)
    DATA = noisy_circles[0]
    klp_kmeans_times3 = []
    klp_kmeans_times3_gpu = []
    kmeans_times3 = []
    for i in range(10, 2001, 100):
        noisy_circles = datasets.make_circles(n_samples=i, factor=.5, noise=.05)
        DATA = noisy_circles[0]

        t1 = time.time()
        W = klp_kmeans(DATA, 1000, alpha=0.001, epochs=1000, batch=10, verbose=False)
        t2 = time.time()

        t5 = time.time()
        W = klp_kmeans(DATA, 1000, alpha=0.001, epochs=1000, batch=10, verbose=False, use_gpu=True)
        t6 = time.time()

        t3 = time.time()
        W2 = kmeans(DATA, 1000, numepochs=1000, batchsize=10, learningrate=0.001, verbose=False)
        t4 = time.time()

        klp_kmeans_times3.append(t2 - t1)
        klp_kmeans_times3_gpu.append(t6 - t5)
        kmeans_times3.append(t4 - t3)

    plt.title('Data Size vs Time')
    plt.plot(range(10, 2001, 100), klp_kmeans_times3, '-o', color='blue')
    plt.xlabel('data_size')
    plt.ylabel('time')
    plt.show()

    plt.plot(range(10, 2001, 100), klp_kmeans_times3_gpu, '-o', color='green')
    plt.show()

    plt.plot(range(10, 2001, 100), kmeans_times3, '-o', color='red')
    plt.show()

    # DATA size test
    print ('DATA dim comparison ----')
    klp_kmeans_times3 = []
    klp_kmeans_times3_gpu = []
    kmeans_times3 = []
    for i in range(100, 4001, 50):
        blobs = datasets.make_blobs(n_samples=4000, random_state=8, n_features=i, centers=10)
        DATA = blobs[0]

        t1 = time.time()
        W = klp_kmeans(DATA, 1000, alpha=0.001, epochs=1000, batch=10, verbose=False)
        t2 = time.time()

        t5 = time.time()
        W = klp_kmeans(DATA, 1000, alpha=0.001, epochs=1000, batch=10, verbose=False, use_gpu=True)
        t6 = time.time()

        t3 = time.time()
        W2 = kmeans(DATA, 1000, numepochs=1000, batchsize=10, learningrate=0.001, verbose=False)
        t4 = time.time()

        klp_kmeans_times3.append(t2 - t1)
        klp_kmeans_times3_gpu.append(t6 - t5)
        kmeans_times3.append(t4 - t3)

    plt.title('Data Dim vs Time')
    plt.plot(range(100, 4001, 50), klp_kmeans_times3, '-o', color='blue')
    plt.xlabel('dims')
    plt.ylabel('time')
    plt.show()

    plt.plot(range(100, 4001, 50), klp_kmeans_times3_gpu, '-o', color='green')
    plt.show()

    plt.plot(range(100, 4001, 50), kmeans_times3, '-o', color='red')
    plt.show()
