import numpy as np
import paramServer as PS
from modelReplica import ModelReplica
from neural_net import NeuralNetwork
import lbfgs



def sliceData(data):
	# This function assumes np.array as the type for data
	# This function separates data into X (features) and Y (label) for the NN
	x = data[:,:-1]
	label_count = PS.get_label_count()
	labels = data[:,-1] # We don't know how many we have due to minibatch size 
	ys = []
	for l in labels: # This sets up probabilities as outputs | 1 per output class
		temp_y = [0 for i in range(label_count)]
		temp_y[int(l)] = 1 # we can cast this because we know labels are ints and not a weird float
		ys.append(temp_y)
	y = ys
	return x,y

def computeGradient(nn, weights, data):
	X, y = sliceData(data) 
	gradients = nn.jac(weights, X, y)
	return gradients

def processPortion(modelReplica, step, nn):
	if(not modelReplica.hasParametersForStep(step)):
		params = PS.getParameters()
		modelReplica.setParams(params, step)
	else:
		params = modelReplica.getParams(step)
	data = PS.getDataPortion()
	gradients = computeGradient(nn, params, data)
	modelReplica.updateAccruedGradients(gradients)




if (__name__ == "__main__"):
	maxHistory = 10 #max number of updates that should be held
	feature_count = PS.get_feature_count()
	label_count = PS.get_label_count()
	layers = [feature_count, 10, label_count] # layers - 1 = hidden layers
	
	nn = NeuralNetwork(layers)
	costFunction = nn.cost
	jacFunction = nn.jac
	step = 0
	len_params = sum(nn.sizes)
	PS.initializeParameters(nn.get_weights())
	modelReplicas = [ModelReplica(len_params)]


	X, y = sliceData(PS.getAllData())
	old_fval = costFunction(PS.getParameters(), X, y)
	old_old_fval = None

	while(step < 100):
		PS.initializeGradients(len_params)

		while(not PS.didFinishBatches()):
			for mr in modelReplicas:
				processPortion(mr, step, nn)
				PS.sendGradients(mr.getLocalAccruedGrad())

		history_S = PS.getHistory_S()
		history_Y = PS.getHistory_Y()
		rho = PS.getRho()
		grad = PS.getAccruedGradients()
		params = PS.getParameters()
		
		#allgrad = nn.jac(params, X, y)

		d_k = lbfgs.computeDirection(maxHistory, step, grad, history_S, history_Y, rho)

		alpha_k, old_fval, old_old_fval, gf_kp1 = lbfgs.lineSearch(costFunction, jacFunction, params, d_k, grad, old_fval, old_old_fval, args=(X,y))

		if(alpha_k is None):
			# Line search failed to find a better solution.
			print "Stopped because line search did not converge"
			break

		PS.updateParameters(step, d_k, alpha_k, maxHistory, gf_kp1)

		step += 1
	print step
	print costFunction(PS.getParameters(), X, y)