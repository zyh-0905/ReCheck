# Executed-result summary

**All intervals are descriptive and conditional on the fixed generator.**

## ReCheck

| method   |   success |   task_loss |   probes_per_task |   objective |   cpu_ms |
|:---------|----------:|------------:|------------------:|------------:|---------:|
| entropy  |  0.919303 |   0.03933   |          0.478928 |   0.0966387 |  1.30208 |
| fresh    |  1        |   0         |          1.21006  |   0.20571   |  1.25722 |
| myopic   |  0.806803 |   0.0760037 |          0.324609 |   0.103795  |  1.23296 |
| never    |  0.622721 |   0.198768  |          0.05     |   0.207268  |  1.12581 |
| no_task  |  0.817329 |   0.0705116 |          0.515278 |   0.119692  |  1.64346 |
| random   |  0.882259 |   0.0537489 |          0.566905 |   0.112838  |  1.36729 |
| recheck  |  0.896723 |   0.0339095 |          0.442752 |   0.0833544 |  1.64379 |
| ttl      |  0.895974 |   0.047328  |          0.437174 |   0.0937657 |  1.29609 |

## RepairLens

| method         |   complete |   normalized_cost |   probes |   planning_ms |   execution_ms |
|:---------------|-----------:|------------------:|---------:|--------------:|---------------:|
| class_entropy  |      1     |          0.828198 |  1.875   |     0.168362  |       0.716083 |
| conservative   |      1     |          0.950612 |  0       |     0         |       0.594405 |
| discard_replay |      1     |          0.821935 |  1.15    |    14.3206    |       0.663451 |
| ec2            |      1     |          0.850411 |  3.54167 |     0.274699  |       0.7175   |
| exact          |      1     |          0.754752 |  1.91667 |    26.3497    |       0.886977 |
| graph_entropy  |      1     |          0.850891 |  3.86667 |     0.26109   |       0.703705 |
| lookahead2     |      1     |          0.766131 |  1.775   |     1.13155   |       0.710799 |
| myopic         |      1     |          0.838139 |  0.525   |     0.132803  |       0.614948 |
| point_estimate |      0.675 |          0.603286 |  0       |     0         |       0.587996 |
| random         |      1     |          1.06495  |  2.675   |     0.0724581 |       0.743345 |
| restart        |      1     |          1        |  0       |     0         |       0.591348 |

## Limitations exposed by execution

- ReCheck improves weighted objective but not every unweighted success comparison.
- RepairLens reduces assigned operation cost, but exact and two-step planning are slower in measured local CPU time than restart.
- RepairLens support omission produces incomplete restoration; the conditional guarantee does not survive missing hypotheses.
- Known finite models, ideal exact observations and deterministic synthetic workers are not end-to-end LLM or public benchmark evidence.