import argparse, time, uuid
from tqdm import tqdm

import torch
import numpy as np
import torchneuromorphic.torchneuromorphic.doublenmnist.doublenmnist_dataloaders as dmnist
import torchneuromorphic.torchneuromorphic.dvs_asl.dvsasl_dataloaders as dvs_asl
import torchneuromorphic.torchneuromorphic.dvs_gestures.dvsgestures_dataloaders as dvs_gestures

from training_curves import plot_curves

from lif_snn import backbone_conv_model, classifier_model, aux_task_gen

torch.manual_seed(42)
if torch.cuda.is_available():
    device = torch.device("cuda")    
    #torch.backends.cudnn.benchmark=True 
else:
    device = torch.device("cpu")
dtype = torch.float32
ms = 1e-3

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--logfile", type=bool, default=False, help='Logfile on')
parser.add_argument("--checkpoint", type=str, default='47c21259-a435-404c-8604-df5dbf0e0063', help='UUID for checkpoint to be tested')
parser.add_argument("--iter-test", type=int, default=25, help='Test Iter')
parser.add_argument("--lr", type=float, default=1.0e-12, help='Learning Rate')
parser.add_argument("--epochs", type=int, default=151, help='Training Epochs') 
parser.add_argument("--batch-size-test", type=int, default=4, help='Batch size')
parser.add_argument("--batch-size-test-test", type=int, default=128, help='Batch size test test')
parser.add_argument("--progressbar-off", type=float, default=True, help='False: progressbar activated')
parser.add_argument("--test-samples", type=int, default=100, help='Number of samples per classes')
parser.add_argument("--n-way", type=int, default=5, help='N-way')
parser.add_argument("--k-shot", type=int, default=5, help='K-shot')
args = parser.parse_args()

checkpoint_dict = torch.load('./checkpoints/'+ args.checkpoint +'.pkl')
args_loaded = checkpoint_dict['arguments']

# training data
if args_loaded.dataset == 'DNMNIST':
    support_ds, query_ds  = dmnist.sample_double_mnist_task(
                meta_dataset_type = 'test',
                N = args.n_way,
                K = args.k_shot,
                K_test = args.test_samples,
                root='data.nosync/nmnist/n_mnist.hdf5',
                batch_size=args.batch_size_test,
                batch_size_test=args.batch_size_test_test,
                ds=args_loaded.downsampling,
                num_workers=4)
    time_steps_train = 300
    time_steps_test = 300
    one_hot_opt = True
elif args_loaded.dataset == 'ASL-DVS':
    train_dl, test_dl  = dvsasl_dataloaders.sample_dvsasl_task(
                meta_dataset_type = 'train',
                N = args.n_train,
                K = args.train_samples,
                K_test = args.train_samples,
                root='data.nosync/dvsasl/dvsasl.hdf5',
                batch_size=args.batch_size,
                batch_size_test=args.batch_size,
                ds=args_loaded.downsampling,
                num_workers=4)
    time_steps_train = 100
    time_steps_test = 100
    one_hot_opt = True
elif args_loaded.dataset == 'DDVSGesture':
    train_dl, test_dl  = sample_double_mnist_task(
                meta_dataset_type = 'train',
                N = args.n_train,
                K = args.train_samples,
                K_test = args.train_samples,
                root='data.nosync/nmnist/n_mnist.hdf5',
                batch_size=args.batch_size,
                batch_size_test=args.batch_size,
                ds=args_loaded.downsampling,
                num_workers=4)
    time_steps_train = 100
    time_steps_test = 100
    one_hot_opt = True
elif args_loaded.dataset == 'DVSGesture':
    train_dl, test_dl  = dvs_gestures.create_dataloader(
                root = 'data.nosync/dvsgesture/dvs_gestures_build.hdf5',
                work_dir = 'data/dvsgesture/',
                batch_size = args.batch_size,
                chunk_size_train = 500,
                chunk_size_test = 1800,
                ds = args_loaded.downsampling,
                dt = 1000,
                transform_train = None,
                transform_test = None,
                target_transform_train = None,
                target_transform_test = None,
                n_events_attention=None,
                num_workers=4)
    time_steps_train = 500
    time_steps_test = 1800
    one_hot_opt = False
else:
    raise Exception("Invalid dataset")


x_preview, y_labels = next(iter(support_ds))
model_uuid = args.checkpoint + str(uuid.uuid4())   


delta_t = args_loaded.delta_t*ms
T = x_preview.shape[1]
acc_point_e = (args.epochs-1)/3

backbone = backbone_conv_model(x_preview = x_preview, in_channels = x_preview.shape[2], oc1 = args_loaded.oc1, oc2 = args_loaded.oc2, oc3 = args_loaded.oc3, k1 = args_loaded.k1, k2 = args_loaded.k2, k3 = args_loaded.k3, padding = args_loaded.padding, bias = args_loaded.conv_bias, tau_ref_low = args_loaded.tau_ref_low*ms, tau_mem_low = args_loaded.tau_mem_low*ms, tau_syn_low = args_loaded.tau_syn_low*ms, tau_ref_high = args_loaded.tau_ref_high*ms, tau_mem_high = args_loaded.tau_mem_high*ms, tau_syn_high = args_loaded.tau_syn_high*ms, thr = args_loaded.thr, gain1 = args_loaded.init_gain_conv1, gain2 = args_loaded.init_gain_conv2, gain3 = args_loaded.init_gain_conv3, delta_t = delta_t, train_t = args_loaded.train_tau, dtype = dtype).to(device)

# load backbone
backbone.load_state_dict(checkpoint_dict['backbone'])
e = checkpoint_dict['epoch']
del checkpoint_dict

if args.logfile:
    with open("logs/test_"+model_uuid+".txt", "a") as file_object:
        file_object.write("\nEvaluating model %s at epoch %d over %d classes with %d examples\n"%(args.checkpoint, e, args.n_way, args.k_shot))
else:
    print("Evaluating model %s at epoch %d over %d classes with %d examples"%(args.checkpoint, e, args.n_way, args.k_shot))

acc_all = [[],[],[]]
for i in range(args.iter_test):
    start_time = time.time()

    # new task
    support_ds, query_ds = dmnist.sample_double_mnist_task(
                meta_dataset_type = 'test',
                N = args.n_way,
                K = args.k_shot,
                K_test = args.test_samples,
                root='data.nosync/nmnist/n_mnist.hdf5',
                batch_size = args.batch_size_test,
                batch_size_test = args.batch_size_test_test,
                ds=args_loaded.downsampling,
                num_workers=4)

    # new classifier
    classifier_nk = classifier_model(T = T, inp_neurons = backbone.f_length, output_classes = args.n_way, tau_ref_low = args_loaded.tau_ref_low*ms, tau_mem_low = args_loaded.tau_mem_low*ms, tau_syn_low = args_loaded.tau_syn_low*ms, tau_ref_high = args_loaded.tau_ref_high*ms, tau_mem_high = args_loaded.tau_mem_high*ms, tau_syn_high = args_loaded.tau_syn_high*ms, bias = args_loaded.fc_bias, thr = args_loaded.thr, gain = args_loaded.init_gain_fc, delta_t = delta_t, train_t = args_loaded.train_tau, dtype = dtype).to(device)

    loss_fn = torch.nn.NLLLoss()
    softmax_pass = torch.nn.LogSoftmax(dim=1)
    opt = torch.optim.Adam([
                {'params': classifier_nk.parameters()}
            ], lr = args_loaded.lr)

    for e in tqdm(range(args.epochs), disable = args.progressbar_off):
        for x_data, y_data in support_ds:
            start_time = time.time()
            x_data = x_data.to(device)
            y_data = y_data.to(device)

            # forwardpass
            with torch.no_grad():
                bb_rr  = backbone(x_data)
            u_rr   = classifier_nk(bb_rr)
            
            # class loss
            class_loss = loss_fn( softmax_pass(u_rr[:,args_loaded.burnin:,:].sum(dim = 1)), y_data)

            # BPTT
            class_loss.backward()
            opt.step()
            opt.zero_grad()

        del x_data, y_data, bb_rr, u_rr, class_loss
        torch.cuda.empty_cache()

        # test data at 100, 200, 300
        if e%acc_point_e == 0 and e != 0:
            test_acc = []
            with torch.no_grad():
                for x_data, y_data in query_ds:
                    start_time = time.time()
                    x_data = x_data.to(device)
                    y_data = y_data.to(device)

                    # forwardpass
                    bb_rr  = backbone(x_data)
                    u_rr   = classifier_nk(bb_rr)

                    test_acc.append((u_rr[:,args_loaded.burnin:,:].sum(dim = 1).argmax(dim=1) == y_data).float())
                    del x_data, y_data, bb_rr, u_rr
                    torch.cuda.empty_cache()
            acc_all[int(e/acc_point_e)-1].append(torch.cat(test_acc).mean().item()*100)
    if args.logfile:
        with open("logs/test_"+model_uuid+".txt", "a") as file_object:
            file_object.write("%d steps reached and the mean acc is %g , %g , %g time %g\n"%(i, np.mean(np.array(acc_all[0])),np.mean(np.array(acc_all[1])),np.mean(np.array(acc_all[2])), time.time() - start_time))
    else:
        print("%d steps reached and the mean acc is %g , %g , %g time %g\n"%(i, np.mean(np.array(acc_all[0])),np.mean(np.array(acc_all[1])),np.mean(np.array(acc_all[2])), time.time() - start_time))


acc_mean1 = np.mean(acc_all[0])
acc_mean2 = np.mean(acc_all[1])
acc_mean3 = np.mean(acc_all[2])
acc_std1  = np.std(acc_all[0])
acc_std2  = np.std(acc_all[1])
acc_std3  = np.std(acc_all[2])
if args.logfile:
    with open("logs/test_"+model_uuid+".txt", "a") as file_object:
        file_object.write('%d Test Acc at %de= %4.2f%% +- %4.2f%%\n' %(args.iter_test, 1*acc_point_e, acc_mean1, 1.96* acc_std1/np.sqrt(args.iter_test)))
        file_object.write('%d Test Acc at %de= %4.2f%% +- %4.2f%%\n' %(args.iter_test, 2*acc_point_e, acc_mean2, 1.96* acc_std2/np.sqrt(args.iter_test)))
        file_object.write('%d Test Acc at %de= %4.2f%% +- %4.2f%%\n' %(args.iter_test, 3*acc_point_e, acc_mean3, 1.96* acc_std3/np.sqrt(args.iter_test)))
else:
    print('%d Test Acc at %de= %4.2f%% +- %4.2f%%\n' %(args.iter_test, 1*acc_point_e, acc_mean1, 1.96* acc_std1/np.sqrt(args.iter_test)))
    print('%d Test Acc at %de= %4.2f%% +- %4.2f%%\n' %(args.iter_test, 2*acc_point_e, acc_mean2, 1.96* acc_std2/np.sqrt(args.iter_test)))
    print('%d Test Acc at %de= %4.2f%% +- %4.2f%%\n' %(args.iter_test, 3*acc_point_e, acc_mean3, 1.96* acc_std3/np.sqrt(args.iter_test)))

