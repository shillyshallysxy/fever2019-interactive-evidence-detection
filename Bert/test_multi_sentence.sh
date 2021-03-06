#!/bin/sh

rm -rf tmp
for SEED in {0..9}
do
     CUDA_VISIBLE_DEVICES=1 python test_multi_sentence.py --task_name ibm-topic --seed ${SEED} --data_dir $1 --bert_model bert-base-uncased --max_seq_length 95 --model_dir "bert_output/bert-base/topic/${SEED}/16batch/" > "ed_multi_sentence_"$SEED".log"

done
