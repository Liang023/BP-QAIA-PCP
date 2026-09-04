\ Model master
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  T + 1000 column_1 + 1000 column_2
Subject To
 each_partition_colored_once_constraint0: column_1 + column_40 + column_101
   + column_3122 + column_3171 + column_3286 + column_3287 + column_3288
   + column_3289 + column_3290 + column_3291 + column_3292 + column_3293
   + column_3294 + column_3295 >= 1
 each_partition_colored_once_constraint1: column_2 + column_66 + column_67
   + column_70 + column_106 + column_107 + column_108 + column_111
   + column_3122 + column_3171 + column_3173 + column_3287 + column_3288
   + column_3289 + column_3290 + column_3291 + column_3292 + column_3298
   + column_3299 + column_3300 + column_3301 + column_3302 + column_3303
   >= 1
 each_partition_colored_once_constraint2: column_1 + column_95
   + column_3122 + column_3171 + column_3173 + column_3286 + column_3287
   + column_3288 + column_3289 + column_3290 + column_3291 + column_3292
   + column_3293 + column_3294 + column_3295 + column_3296 + column_3297
   + column_3298 + column_3299 + column_3300 + column_3301 + column_3302
   + column_3303 + column_3304 + column_3305 >= 1
 each_partition_colored_once_constraint3: column_2 + column_95
   + column_3122 + column_3171 + column_3173 + column_3288 + column_3290
   + column_3295 + column_3299 + column_3301 + column_3304 + column_3305
   >= 1
 each_partition_colored_once_constraint4: column_1 + column_4 + column_66
   + column_67 + column_70 + column_106 + column_107 + column_108
   + column_111 + column_3286 + column_3287 + column_3288 + column_3289
   + column_3290 + column_3291 + column_3292 + column_3293 + column_3294
   + column_3295 + column_3296 + column_3297 + column_3298 + column_3299
   + column_3300 + column_3301 + column_3302 + column_3303 + column_3304
   + column_3305 >= 1
 each_partition_colored_once_constraint5: column_2 + column_4 + column_77
   + column_106 + column_107 + column_108 + column_111 + column_3122 >= 1
 each_partition_colored_once_constraint6: column_1 + column_4 + column_95
   + column_106 + column_107 + column_108 + column_111 + column_3286
   + column_3287 + column_3288 + column_3289 + column_3290 + column_3291
   + column_3292 + column_3293 + column_3294 + column_3295 + column_3296
   + column_3297 + column_3298 + column_3299 + column_3300 + column_3301
   + column_3302 + column_3303 + column_3304 + column_3305 >= 1
 each_partition_colored_once_constraint7: column_2 + column_36 + column_40
   + column_97 + column_101 + column_3122 + column_3171 + column_3173
   + column_3296 + column_3297 + column_3298 + column_3299 + column_3300
   + column_3301 + column_3302 + column_3303 + column_3304 + column_3305
   >= 1
 each_partition_colored_once_constraint8: column_1 + column_5 + column_66
   + column_67 + column_70 + column_77 + column_95 + column_106
   + column_107 + column_108 + column_111 + column_3296 + column_3297
   + column_3298 + column_3299 + column_3300 + column_3301 + column_3302
   + column_3303 + column_3304 + column_3305 >= 1
 each_partition_colored_once_constraint9: column_2 + column_77 + column_106
   + column_107 + column_108 + column_111 + column_3171 + column_3173 >= 1
 makespan_vertex_0: T - column_1 >= 0
 makespan_vertex_1: T >= 0
 makespan_vertex_2: T - column_40 - column_101 - column_3122 - column_3171
   - column_3286 - column_3287 - column_3288 - column_3289 - column_3290
   - column_3291 - column_3292 - column_3293 - column_3294 - column_3295
   >= 0
 makespan_vertex_3: T >= 0
 makespan_vertex_4: T - 2 column_2 - 2 column_66 - 2 column_106
   - 2 column_107 - 2 column_3122 - 2 column_3171 - 2 column_3173
   - 2 column_3287 - 2 column_3288 - 2 column_3290 - 2 column_3291
   - 2 column_3298 - 2 column_3299 - 2 column_3301 - 2 column_3302 >= 0
 makespan_vertex_5: T - 4 column_67 - 4 column_108 - 4 column_3289
   - 4 column_3300 >= 0
 makespan_vertex_6: T - 4 column_70 - 4 column_111 - 4 column_3292
   - 4 column_3303 >= 0
 makespan_vertex_7: T - 3 column_1 - 3 column_95 - 3 column_3122
   - 3 column_3171 - 3 column_3173 - 3 column_3288 - 3 column_3290
   - 3 column_3295 - 3 column_3299 - 3 column_3301 - 3 column_3304
   - 3 column_3305 >= 0
 makespan_vertex_8: T - 12 column_3286 - 12 column_3287 - 12 column_3289
   - 12 column_3291 - 12 column_3292 - 12 column_3293 - 12 column_3294
   - 12 column_3296 - 12 column_3297 - 12 column_3298 - 12 column_3300
   - 12 column_3302 - 12 column_3303 >= 0
 makespan_vertex_9: T - 4 column_2 - 4 column_95 - 4 column_3122
   - 4 column_3171 - 4 column_3173 - 4 column_3288 - 4 column_3290
   - 4 column_3295 - 4 column_3299 - 4 column_3301 - 4 column_3304
   - 4 column_3305 >= 0
 makespan_vertex_10: T >= 0
 makespan_vertex_11: T - 5 column_1 - 5 column_66 - 5 column_67
   - 5 column_70 - 5 column_106 - 5 column_108 - 5 column_111
   - 5 column_3286 - 5 column_3287 - 5 column_3288 - 5 column_3289
   - 5 column_3292 - 5 column_3295 - 5 column_3297 - 5 column_3298
   - 5 column_3299 - 5 column_3300 - 5 column_3303 - 5 column_3304 >= 0
 makespan_vertex_12: T - 9 column_3294 >= 0
 makespan_vertex_13: T - 2 column_4 >= 0
 makespan_vertex_14: T - 10 column_107 - 10 column_3290 - 10 column_3291
   - 10 column_3293 - 10 column_3296 - 10 column_3301 - 10 column_3302
   - 10 column_3305 >= 0
 makespan_vertex_15: T - 6 column_2 - 6 column_77 - 6 column_106
   - 6 column_107 - 6 column_108 - 6 column_111 - 6 column_3122 >= 0
 makespan_vertex_16: T - column_4 >= 0
 makespan_vertex_17: T >= 0
 makespan_vertex_18: T - 7 column_1 - 7 column_95 - 7 column_106
   - 7 column_107 - 7 column_108 - 7 column_111 - 7 column_3286
   - 7 column_3287 - 7 column_3288 - 7 column_3289 - 7 column_3290
   - 7 column_3291 - 7 column_3292 - 7 column_3293 - 7 column_3294
   - 7 column_3295 - 7 column_3296 - 7 column_3297 - 7 column_3298
   - 7 column_3299 - 7 column_3300 - 7 column_3301 - 7 column_3302
   - 7 column_3303 - 7 column_3304 - 7 column_3305 >= 0
 makespan_vertex_19: T - 4 column_4 >= 0
 makespan_vertex_20: T - 8 column_2 - 8 column_97 - 8 column_101
   - 8 column_3122 - 8 column_3171 - 8 column_3173 - 8 column_3296
   - 8 column_3297 - 8 column_3298 - 8 column_3299 - 8 column_3300
   - 8 column_3301 - 8 column_3302 - 8 column_3303 - 8 column_3304
   - 8 column_3305 >= 0
 makespan_vertex_21: T - 9 column_36 - 9 column_40 >= 0
 makespan_vertex_22: T - 9 column_1 >= 0
 makespan_vertex_23: T - column_5 - column_66 - column_67 - column_70
   - column_77 - column_95 - column_106 - column_107 - column_108
   - column_111 - column_3296 - column_3297 - column_3298 - column_3299
   - column_3300 - column_3301 - column_3302 - column_3303 - column_3304
   - column_3305 >= 0
 makespan_vertex_24: T >= 0
 makespan_vertex_25: T >= 0
 makespan_vertex_26: T - 10 column_2 >= 0
 makespan_vertex_27: T >= 0
 makespan_vertex_28: T >= 0
 makespan_vertex_29: T - 9 column_77 - 9 column_106 - 9 column_107
   - 9 column_108 - 9 column_111 - 9 column_3171 - 9 column_3173 >= 0
 charger_capacity_constraint: column_1 + column_2 + column_4 + column_5
   + column_36 + column_40 + column_66 + column_67 + column_70 + column_77
   + column_95 + column_97 + column_101 + column_106 + column_107
   + column_108 + column_111 + column_3122 + column_3171 + column_3173
   + column_3286 + column_3287 + column_3288 + column_3289 + column_3290
   + column_3291 + column_3292 + column_3293 + column_3294 + column_3295
   + column_3296 + column_3297 + column_3298 + column_3299 + column_3300
   + column_3301 + column_3302 + column_3303 + column_3304 + column_3305
   <= 2
Bounds
End
