\ Model master
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  T + 1000 column_1 + 1000 column_2
Subject To
 each_partition_colored_once_constraint0: column_1 + column_98 + column_100
   + column_102 + column_3096 + column_3097 + column_3099 + column_3106
   + column_3366 + column_3369 + column_3371 + column_3373 + column_3375
   >= 1
 each_partition_colored_once_constraint1: column_2 + column_66 + column_100
   + column_102 + column_3097 + column_3099 + column_3239 + column_3242
   + column_3368 + column_3369 + column_3371 + column_3372 >= 1
 each_partition_colored_once_constraint2: column_1 + column_102
   + column_3099 + column_3238 + column_3239 + column_3240 + column_3241
   + column_3242 + column_3370 + column_3371 + column_3372 + column_3373
   + column_3375 >= 1
 each_partition_colored_once_constraint3: column_2 + column_3096
   + column_3097 + column_3099 + column_3106 + column_3238 + column_3239
   + column_3240 + column_3241 + column_3242 >= 1
 each_partition_colored_once_constraint4: column_1 + column_4 + column_66
   + column_3106 + column_3238 + column_3239 + column_3240 + column_3241
   + column_3242 + column_3374 + column_3375 >= 1
 each_partition_colored_once_constraint5: column_2 + column_4 + column_3096
   + column_3097 + column_3099 + column_3106 + column_3238 + column_3239
   + column_3240 + column_3241 + column_3242 >= 1
 each_partition_colored_once_constraint6: column_1 + column_4 + column_3106
   >= 1
 each_partition_colored_once_constraint7: column_2 + column_97 + column_98
   + column_100 + column_102 + column_3106 + column_3238 + column_3239
   + column_3240 + column_3241 + column_3242 >= 1
 each_partition_colored_once_constraint8: column_1 + column_5 + column_66
   + column_3238 + column_3239 + column_3240 + column_3241 + column_3242
   + column_3367 + column_3368 + column_3370 + column_3372 + column_3374
   >= 1
 each_partition_colored_once_constraint9: column_2 + column_3366
   + column_3367 + column_3368 + column_3369 + column_3370 + column_3371
   + column_3372 + column_3373 + column_3374 + column_3375 >= 1
 makespan_vertex_0: T - column_1 - column_98 - column_100 - column_102
   - column_3096 - column_3097 - column_3099 - column_3106 - column_3366
   - column_3369 - column_3371 - column_3373 - column_3375 >= 0
 makespan_vertex_1: T >= 0
 makespan_vertex_2: T >= 0
 makespan_vertex_3: T >= 0
 makespan_vertex_4: T - 2 column_2 - 2 column_66 - 2 column_100
   - 2 column_102 - 2 column_3097 - 2 column_3099 - 2 column_3239
   - 2 column_3242 - 2 column_3368 - 2 column_3369 - 2 column_3371
   - 2 column_3372 >= 0
 makespan_vertex_5: T >= 0
 makespan_vertex_6: T >= 0
 makespan_vertex_7: T - 3 column_1 - 3 column_102 - 3 column_3099
   - 3 column_3238 - 3 column_3239 - 3 column_3240 - 3 column_3241
   - 3 column_3242 - 3 column_3370 - 3 column_3371 - 3 column_3372
   - 3 column_3373 - 3 column_3375 >= 0
 makespan_vertex_8: T >= 0
 makespan_vertex_9: T - 4 column_2 - 4 column_3096 - 4 column_3097
   - 4 column_3099 - 4 column_3106 - 4 column_3238 - 4 column_3239
   - 4 column_3240 - 4 column_3241 - 4 column_3242 >= 0
 makespan_vertex_10: T >= 0
 makespan_vertex_11: T - 5 column_1 - 5 column_66 - 5 column_3106
   - 5 column_3238 - 5 column_3239 - 5 column_3374 - 5 column_3375 >= 0
 makespan_vertex_12: T - 9 column_3240 - 9 column_3242 >= 0
 makespan_vertex_13: T - 2 column_4 - 2 column_3241 >= 0
 makespan_vertex_14: T >= 0
 makespan_vertex_15: T - 6 column_2 - 6 column_3096 - 6 column_3097
   - 6 column_3099 - 6 column_3106 - 6 column_3238 - 6 column_3239
   - 6 column_3240 - 6 column_3241 - 6 column_3242 >= 0
 makespan_vertex_16: T - column_4 >= 0
 makespan_vertex_17: T >= 0
 makespan_vertex_18: T - 7 column_1 - 7 column_3106 >= 0
 makespan_vertex_19: T - 4 column_4 >= 0
 makespan_vertex_20: T - 8 column_2 - 8 column_97 - 8 column_98
   - 8 column_100 - 8 column_102 - 8 column_3106 - 8 column_3238
   - 8 column_3239 - 8 column_3240 - 8 column_3241 - 8 column_3242 >= 0
 makespan_vertex_21: T >= 0
 makespan_vertex_22: T - 9 column_1 >= 0
 makespan_vertex_23: T - column_5 - column_66 - column_3238 - column_3239
   - column_3240 - column_3241 - column_3242 - column_3367 - column_3368
   - column_3370 - column_3372 - column_3374 >= 0
 makespan_vertex_24: T >= 0
 makespan_vertex_25: T >= 0
 makespan_vertex_26: T - 10 column_2 >= 0
 makespan_vertex_27: T >= 0
 makespan_vertex_28: T >= 0
 makespan_vertex_29: T - 9 column_3366 - 9 column_3367 - 9 column_3368
   - 9 column_3369 - 9 column_3370 - 9 column_3371 - 9 column_3372
   - 9 column_3373 - 9 column_3374 - 9 column_3375 >= 0
 charger_capacity_constraint: column_1 + column_2 + column_4 + column_5
   + column_66 + column_97 + column_98 + column_100 + column_102
   + column_3096 + column_3097 + column_3099 + column_3106 + column_3238
   + column_3239 + column_3240 + column_3241 + column_3242 + column_3366
   + column_3367 + column_3368 + column_3369 + column_3370 + column_3371
   + column_3372 + column_3373 + column_3374 + column_3375 <= 2
Bounds
End
