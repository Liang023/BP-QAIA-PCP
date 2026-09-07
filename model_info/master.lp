\ Model master
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  T + 1000 column_1 + 1000 column_2
Subject To
 each_partition_colored_once_constraint0: column_1 + column_48 + column_342
   + column_347 + column_348 + column_810 + column_1536 >= 1
 each_partition_colored_once_constraint1: column_2 + column_48
   + column_1536 + column_1538 + column_1542 >= 1
 each_partition_colored_once_constraint2: column_1 + column_342
   + column_343 + column_347 + column_348 + column_810 + column_1542 >= 1
 each_partition_colored_once_constraint3: column_2 + column_48 + column_68
   + column_342 + column_810 + column_1539 + column_1542 >= 1
 each_partition_colored_once_constraint4: column_1 + column_342
   + column_810 + column_1536 + column_1542 >= 1
 each_partition_colored_once_constraint5: column_2 + column_68 + column_343
   + column_810 + column_1536 + column_1542 >= 1
 each_partition_colored_once_constraint6: column_1 + column_68 + column_107
   + column_343 + column_347 + column_348 + column_1536 + column_1539 >= 1
 each_partition_colored_once_constraint7: column_2 + column_48 + column_342
   + column_347 + column_348 + column_1536 >= 1
 each_partition_colored_once_constraint8: column_1 + column_68 + column_106
   + column_342 + column_347 + column_348 + column_1536 + column_1539
   + column_1542 >= 1
 each_partition_colored_once_constraint9: column_2 + column_342
   + column_343 + column_347 + column_348 + column_810 + column_1538
   + column_1539 >= 1
 makespan_vertex_0: T - column_1 >= 0
 makespan_vertex_1: T - 2 column_48 - 2 column_342 - 2 column_347
   - 2 column_348 - 2 column_810 - 2 column_1536 >= 0
 makespan_vertex_2: T >= 0
 makespan_vertex_3: T >= 0
 makespan_vertex_4: T - 2 column_2 >= 0
 makespan_vertex_5: T >= 0
 makespan_vertex_6: T - 4 column_48 - 4 column_1536 - 4 column_1538
   - 4 column_1542 >= 0
 makespan_vertex_7: T - 3 column_1 - 3 column_342 - 3 column_343
   - 3 column_347 - 3 column_348 - 3 column_810 - 3 column_1542 >= 0
 makespan_vertex_8: T >= 0
 makespan_vertex_9: T - 4 column_2 >= 0
 makespan_vertex_10: T - 11 column_48 - 11 column_68 - 11 column_342
   - 11 column_810 - 11 column_1539 - 11 column_1542 >= 0
 makespan_vertex_11: T - 5 column_1 >= 0
 makespan_vertex_12: T - 9 column_810 >= 0
 makespan_vertex_13: T >= 0
 makespan_vertex_14: T - 10 column_342 - 10 column_1536 - 10 column_1542
   >= 0
 makespan_vertex_15: T - 6 column_2 >= 0
 makespan_vertex_16: T - column_68 - column_343 - column_810 - column_1536
   - column_1542 >= 0
 makespan_vertex_17: T >= 0
 makespan_vertex_18: T - 7 column_1 - 7 column_68 - 7 column_1536
   - 7 column_1539 >= 0
 makespan_vertex_19: T - 4 column_107 - 4 column_343 - 4 column_347
   - 4 column_348 >= 0
 makespan_vertex_20: T - 8 column_2 - 8 column_48 - 8 column_342
   - 8 column_347 - 8 column_348 - 8 column_1536 >= 0
 makespan_vertex_21: T >= 0
 makespan_vertex_22: T - 9 column_1 - 9 column_68 - 9 column_342
   - 9 column_347 - 9 column_348 - 9 column_1536 - 9 column_1542 >= 0
 makespan_vertex_23: T >= 0
 makespan_vertex_24: T >= 0
 makespan_vertex_25: T - 4 column_106 - 4 column_1539 >= 0
 makespan_vertex_26: T - 10 column_2 >= 0
 makespan_vertex_27: T - 11 column_343 - 11 column_347 - 11 column_1538
   >= 0
 makespan_vertex_28: T - 12 column_342 - 12 column_348 - 12 column_810
   - 12 column_1539 >= 0
 makespan_vertex_29: T >= 0
 charger_capacity_constraint: column_1 + column_2 + column_48 + column_68
   + column_106 + column_107 + column_342 + column_343 + column_347
   + column_348 + column_810 + column_1536 + column_1538 + column_1539
   + column_1542 <= 2
Bounds
End
