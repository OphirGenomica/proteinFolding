import time

import matplotlib

from src.loss import loss_tr_tuples
from src.utils import move_tuple_to
from src.visualization import compare_distogram, plotfullprotein

# from torch_lr_finder import LRFinder

matplotlib.use('Agg')

import torch

def train(net,optimizer,dataloader_train,loss_fnc,LOG,device='cpu',dl_test=None,ite=0,max_iter=100000,report_iter=1e4,checkpoint=1e19, scheduler=None, sigma=-1):
    '''
    Standard training routine.
    :param net: Network to train
    :param optimizer: Optimizer to use
    :param dataloader_train: data to train on
    :param loss_fnc: loss function to use
    :param LOG: LOG file handler to print to
    :param device: device to perform computation on
    :param dataloader_test: Dataloader to test the accuracy on after each epoch.
    :param epochs: Number of epochs to train
    :return:
    '''
    stop_run = False
    net.to(device)
    t0 = time.time()
    t1 = time.time()
    loss_train_d = 0
    loss_train_c = 0
    loss_train = 0

    while True:
        for i,(seq, dists,mask, coords) in enumerate(dataloader_train):
            seq = seq.to(device, non_blocking=True)
            mask = mask.to(device, non_blocking=True) # Note that this is the padding mask, and not the mask for targets that are not available.
            dists = move_tuple_to(dists, device, non_blocking=True)
            coords = move_tuple_to(coords, device, non_blocking=True)

            w = ite / max_iter
            optimizer.zero_grad()
            dists_pred, coords_pred = net(seq,mask)

            loss_d = loss_fnc(dists_pred, dists)
            if coords_pred is not None and sigma<0:
                loss_c = loss_tr_tuples(coords_pred, coords)
                loss_train_c += loss_c.cpu().detach()
                loss = (1-w) * loss_d + w * loss_c
            else:
                loss = loss_d

            loss.backward()
            optimizer.step()
            loss_train_d += loss_d.cpu().detach()
            loss_train += loss.cpu().detach()

            if scheduler is not None:
                scheduler.step()

            if (ite + 1) % report_iter == 0:
                if dl_test is not None:
                    t2 = time.time()
                    loss_v, dist_err_ang = eval_net(net, dl_test, loss_fnc, device=device, plot_results=False)
                    t3 = time.time()
                    if scheduler is None:
                        lr = optimizer.param_groups[0]['lr']
                    else:
                        lr = scheduler.get_last_lr()[0]
                    LOG.info(
                        '{:6d}/{:6d}  Loss(training): {:6.4f}%  Loss(test): {:6.4f}%  Loss(dist): {:6.4f}%  Loss(coord): {:6.4f}%  Dist_err(ang): {:2.2f}  LR: {:.8}  Time(train): {:.2f}s  Time(test): {:.2f}s  Time(total): {:.2f}h  ETA: {:.2f}h'.format(
                            ite + 1,int(max_iter), loss_train/report_iter*100, loss_v*100, loss_train_d/report_iter*100, loss_train_c/report_iter*100, dist_err_ang, lr, t2-t1, t3 - t2, (t3 - t0)/3600,(max_iter-ite+1)/(ite+1)*(t3-t0)/3600))
                    t1 = time.time()
                    loss_train_d = 0
                    loss_train_c = 0
                    loss_train = 0
            if (ite + 1) % checkpoint == 0:
                pass
                # filename = "{}{}_checkpoint.tar".format(save, ite + 1)
                # save_checkpoint(ite + 1, net.state_dict(), optimizer.state_dict(), filename=filename)
                # LOG.info("Checkpoint saved: {}".format(filename))
            ite += 1

            if ite >= max_iter:
                stop_run = True
                break
        if stop_run:
            break
    # plotfullprotein(cnn_pred, caa_pred, cbb_pred, cnn_target, caa_target, cbb_target)
    # plotcoordinates(pred, target_coord)
    return net


def eval_net(net, dl, loss_fnc, device='cpu', plot_results=False, save_results=False):
    '''
    Standard training routine.
    :param net: Network to train
    :param optimizer: Optimizer to use
    :param dataloader_train: data to train on
    :param loss_fnc: loss function to use
    :param device: device to perform computation on
    :param dataloader_test: Dataloader to test the accuracy on after each epoch.
    :param epochs: Number of epochs to train
    :return:
    '''
    net.to(device)
    net.eval()
    with torch.no_grad():
        loss_v = 0
        dist_err_angstrom = 0
        for i,(seq, dists,mask, coords) in enumerate(dl):
            seq = seq.to(device, non_blocking=True)
            dists = move_tuple_to(dists, device, non_blocking=True)
            coords = move_tuple_to(coords, device, non_blocking=True)
            mask = mask.to(device, non_blocking=True)  # Note that this is the padding mask, and not the mask for targets that are not available.
            dists_pred, coords_pred = net(seq,mask)
            loss_d = loss_fnc(dists_pred, dists)
            if coords_pred is not None:
                loss_c, coords_pred_tr, coords_tr = loss_tr_tuples(coords_pred, coords, return_coords=True)
                loss = 0.5 * loss_d + 0.5 * loss_c
            else:
                loss = loss_d
            loss_v += loss

            dist_err_angstrom += torch.sum(torch.sqrt(torch.mean((dists_pred[0] - dists[0])**2,dim=(1,2)))*10)

            if save_results:
                compare_distogram(dists_pred, dists, mask, save_results="{:}dist_{:}".format(save_results,i))
                plotfullprotein(coords_pred_tr, coords_tr, save_results="{:}coord_{:}".format(save_results,i))
        if plot_results :
            compare_distogram(dists_pred, dists, mask, plot_results=plot_results)
            plotfullprotein(coords_pred_tr, coords_tr, plot_results=plot_results)
    net.train()
    return loss_v/len(dl), dist_err_angstrom/len(dl.dataset)




def net_prediction(net, dl, device='cpu', plot_results=False, save_results=False):
    '''
    Standard training routine.
    :param net: Network to train
    :param optimizer: Optimizer to use
    :param dataloader_train: data to train on
    :param loss_fnc: loss function to use
    :param device: device to perform computation on
    :param dataloader_test: Dataloader to test the accuracy on after each epoch.
    :param epochs: Number of epochs to train
    :return:
    '''
    net.to(device)
    net.eval()
    with torch.no_grad():
        loss_v = 0
        dist_err_angstrom = 0
        for i,(seq, dists,mask, coords) in enumerate(dl):
            seq = seq.to(device, non_blocking=True)
            dists = move_tuple_to(dists, device, non_blocking=True)
            coords = move_tuple_to(coords, device, non_blocking=True)
            mask = mask.to(device, non_blocking=True)  # Note that this is the padding mask, and not the mask for targets that are not available.
            dists_pred, coords_pred = net(seq,mask)
            _, coords_pred_tr, coords_tr = loss_tr_tuples(coords_pred, coords, return_coords=True)
            dist_err_angstrom += torch.sum(torch.sqrt(torch.mean((dists_pred[0] - dists[0]) ** 2, dim=(1, 2))) * 10)
            if save_results:
                compare_distogram(dists_pred, dists, mask, save_results="{:}dist_{:}".format(save_results,i))
                plotfullprotein(coords_pred_tr, coords_tr, save_results="{:}coord_{:}".format(save_results,i))
        if plot_results :
            compare_distogram(dists_pred, dists, mask, plot_results=plot_results)
            plotfullprotein(coords_pred_tr, coords_tr, plot_results=plot_results)
        dist_err_angstrom /= len(dl.dataset)
        print("Average distogram error in angstrom = {:2.2f}".format(dist_err_angstrom))
    net.train()
    return

