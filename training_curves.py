import matplotlib.pyplot as plt

def plot_curves(acc_hist, aux_hist, clal_hist, auxl_hist, act1_hist, act2_hist, act3_hist, act4_hist, actA_hist, model_uuid):
    plt.clf()
    fig, axes = plt.subplots(nrows=3, ncols=1) 
    axes[0].plot(clal_hist, label = "Classification Loss", color = 'tab:blue')
    temp_x = axes[0].twinx()
    temp_x.plot(auxl_hist, label = "Rotation Loss", color = 'tab:orange')
    axes[0].set_xlabel("Epochs")
    axes[0].set_ylabel("Loss Class")
    temp_x.set_ylabel("Loss Aux")
    axes[0].legend()

    axes[1].plot(acc_hist, label = "Classification Acc", color = 'tab:blue')
    temp_x = axes[1].twinx()
    temp_x.plot(aux_hist, label = "Rotation Acc", color = 'tab:orange')
    axes[1].set_xlabel("Epochs")
    axes[1].set_ylabel("Acc Class")
    temp_x.set_ylabel("Acc Aux")
    axes[1].legend()

    axes[2].plot(act1_hist, label = "Conv1 Spikes")
    axes[2].plot(act2_hist, label = "Conv2 Spikes")
    axes[2].plot(act3_hist, label = "Conv3 Spikes")
    axes[2].plot(actA_hist, label = "FC Aux Spikes")
    axes[2].plot(act4_hist, label = "FC Cla Spikes")
    axes[2].set_xlabel("Epochs")
    axes[2].set_ylabel("# Spikes")
    axes[2].legend()

    plt.tight_layout()
    plt.savefig("figures/"+ model_uuid + ".png")
    plt.close()
