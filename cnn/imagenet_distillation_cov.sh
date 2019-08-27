#!/bin/bash
# for layer in layers.6.conv2 layers.7.conv2 layers.8.conv2 layers.9.conv2 layers.10.conv2 layers.11.conv2 layers.12.conv2; do
#     # for nblocks in $(seq 1 10); do
#     for nblocks in 1 2 4 6 8 12; do
#         python distill_cov_experiment.py with optimizer=Adam model_args.layer=$layer model_args.nblocks=$nblocks &
#         sleep 2m
#     done
#     sleep 10m
# done
# sleep 30m

for layer in layers.6.conv2 layers.7.conv2 layers.8.conv2 layers.9.conv2 layers.10.conv2 layers.11.conv2 layers.12.conv2; do
    for nblocks in 1 2 4 6 8 12; do
        python distill_cov_experiment.py with teacher_model=mobilenetv1_0.5 objective=frob optimizer=Adam model_args.layer=$layer model_args.nblocks=$nblocks &
        sleep 2m
    done
    sleep 10m
done
sleep 20m

for layer in layers.6.conv2 layers.7.conv2 layers.8.conv2 layers.9.conv2 layers.10.conv2 layers.11.conv2 layers.12.conv2; do
    for nblocks in 1 2 4 6 8 12; do
        python distill_cov_experiment.py with teacher_model=mobilenetv1 objective=cov optimizer=Adam model_args.layer=$layer model_args.nblocks=$nblocks &
        sleep 2m
    done
    sleep 10m
done
sleep 20m

for layer in layers.6.conv2 layers.7.conv2 layers.8.conv2 layers.9.conv2 layers.10.conv2 layers.11.conv2 layers.12.conv2; do
    for nblocks in 1 2 4 6 8 12; do
        python distill_cov_experiment.py with teacher_model=mobilenetv1 objective=frob optimizer=Adam model_args.layer=$layer model_args.nblocks=$nblocks &
        sleep 2m
    done
    sleep 10m
done
sleep 20m