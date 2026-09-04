\ Model master
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  T + 1000 column_1 + 1000 column_2
Subject To
 each_partition_colored_once_constraint0: column_1 + column_40
   + column_3286 + column_3287 + column_3288 + column_3289 + column_3290
   + column_3291 + column_3292 + column_3293 + column_3294 + column_3295
   + column_3306 + column_3309 + column_3311 + column_3313 + column_3317
   + column_3319 + column_3321 + column_3323 + column_3326 + column_3329
   + column_3331 + column_3333 >= 1
 each_partition_colored_once_constraint1: column_2 + column_66 + column_67
   + column_70 + column_106 + column_107 + column_108 + column_111
   + column_3287 + column_3288 + column_3289 + column_3290 + column_3291
   + column_3292 + column_3308 + column_3309 + column_3310 + column_3311
   + column_3312 + column_3313 + column_3314 + column_3315 + column_3318
   + column_3319 + column_3320 + column_3321 + column_3322 + column_3323
   + column_3324 + column_3325 + column_3328 + column_3329 + column_3330
   + column_3331 + column_3332 + column_3333 + column_3334 + column_3335
   >= 1
 each_partition_colored_once_constraint2: column_1 + column_95
   + column_3286 + column_3287 + column_3288 + column_3289 + column_3290
   + column_3291 + column_3292 + column_3293 + column_3294 + column_3295
   + column_3306 + column_3307 + column_3308 + column_3309 + column_3310
   + column_3311 + column_3312 + column_3313 + column_3314 + column_3315
   + column_3316 + column_3317 + column_3318 + column_3319 + column_3320
   + column_3321 + column_3322 + column_3323 + column_3324 + column_3325
   + column_3326 + column_3327 + column_3328 + column_3329 + column_3330
   + column_3331 + column_3332 + column_3333 + column_3334 + column_3335
   >= 1
 each_partition_colored_once_constraint3: column_2 + column_95
   + column_3288 + column_3290 + column_3295 + column_3310 + column_3311
   + column_3320 + column_3321 + column_3330 + column_3331 >= 1
 each_partition_colored_once_constraint4: column_1 + column_4 + column_66
   + column_67 + column_70 + column_106 + column_107 + column_108
   + column_111 + column_3286 + column_3287 + column_3288 + column_3289
   + column_3290 + column_3291 + column_3292 + column_3293 + column_3294
   + column_3295 + column_3315 + column_3325 + column_3335 >= 1
 each_partition_colored_once_constraint5: column_2 + column_4 + column_77
   + column_106 + column_107 + column_108 + column_111 + column_3306
   + column_3307 + column_3308 + column_3309 + column_3310 + column_3311
   + column_3312 + column_3313 + column_3314 + column_3315 >= 1
 each_partition_colored_once_constraint6: column_1 + column_4 + column_95
   + column_106 + column_107 + column_108 + column_111 + column_3286
   + column_3287 + column_3288 + column_3289 + column_3290 + column_3291
   + column_3292 + column_3293 + column_3294 + column_3295 + column_3326
   + column_3327 + column_3328 + column_3329 + column_3330 + column_3331
   + column_3332 + column_3333 + column_3334 + column_3335 >= 1
 each_partition_colored_once_constraint7: column_2 + column_36 + column_40
   + column_3306 + column_3307 + column_3308 + column_3309 + column_3310
   + column_3311 + column_3312 + column_3313 + column_3314 + column_3315
   + column_3326 + column_3327 + column_3328 + column_3329 + column_3330
   + column_3331 + column_3332 + column_3333 + column_3334 + column_3335
   >= 1
 each_partition_colored_once_constraint8: column_1 + column_5 + column_66
   + column_67 + column_70 + column_77 + column_95 + column_106
   + column_107 + column_108 + column_111 + column_3307 + column_3308
   + column_3310 + column_3312 + column_3314 + column_3315 + column_3316
   + column_3318 + column_3320 + column_3322 + column_3324 + column_3325
   + column_3327 + column_3328 + column_3330 + column_3332 + column_3334
   + column_3335 >= 1
 each_partition_colored_once_constraint9: column_2 + column_77 + column_106
   + column_107 + column_108 + column_111 + column_3316 + column_3317
   + column_3318 + column_3319 + column_3320 + column_3321 + column_3322
   + column_3323 + column_3324 + column_3325 >= 1
 makespan_vertex_0: T - column_1 >= 0
 makespan_vertex_1: T >= 0
 makespan_vertex_2: T - column_40 - column_3286 - column_3287 - column_3288
   - column_3289 - column_3290 - column_3291 - column_3292 - column_3293
   - column_3294 - column_3295 - column_3306 - column_3309 - column_3311
   - column_3313 - column_3317 - column_3319 - column_3321 - column_3323
   - column_3326 - column_3329 - column_3331 - column_3333 >= 0
 makespan_vertex_3: T >= 0
 makespan_vertex_4: T - 2 column_2 - 2 column_66 - 2 column_106
   - 2 column_107 - 2 column_3287 - 2 column_3288 - 2 column_3290
   - 2 column_3291 - 2 column_3308 - 2 column_3309 - 2 column_3310
   - 2 column_3311 - 2 column_3315 - 2 column_3318 - 2 column_3319
   - 2 column_3320 - 2 column_3321 - 2 column_3325 - 2 column_3328
   - 2 column_3329 - 2 column_3330 - 2 column_3331 - 2 column_3335 >= 0
 makespan_vertex_5: T - 4 column_67 - 4 column_108 - 4 column_3289
   - 4 column_3312 - 4 column_3313 - 4 column_3322 - 4 column_3323
   - 4 column_3332 - 4 column_3333 >= 0
 makespan_vertex_6: T - 4 column_70 - 4 column_111 - 4 column_3292
   - 4 column_3314 - 4 column_3324 - 4 column_3334 >= 0
 makespan_vertex_7: T - 3 column_1 - 3 column_95 - 3 column_3288
   - 3 column_3290 - 3 column_3295 - 3 column_3310 - 3 column_3311
   - 3 column_3320 - 3 column_3321 - 3 column_3330 - 3 column_3331 >= 0
 makespan_vertex_8: T - 12 column_3286 - 12 column_3287 - 12 column_3289
   - 12 column_3291 - 12 column_3292 - 12 column_3293 - 12 column_3294
   - 12 column_3306 - 12 column_3307 - 12 column_3308 - 12 column_3309
   - 12 column_3312 - 12 column_3313 - 12 column_3314 - 12 column_3315
   - 12 column_3316 - 12 column_3317 - 12 column_3318 - 12 column_3319
   - 12 column_3322 - 12 column_3323 - 12 column_3324 - 12 column_3325
   - 12 column_3326 - 12 column_3327 - 12 column_3328 - 12 column_3329
   - 12 column_3332 - 12 column_3333 - 12 column_3334 - 12 column_3335
   >= 0
 makespan_vertex_9: T - 4 column_2 - 4 column_95 - 4 column_3288
   - 4 column_3290 - 4 column_3295 - 4 column_3310 - 4 column_3311
   - 4 column_3320 - 4 column_3321 - 4 column_3330 - 4 column_3331 >= 0
 makespan_vertex_10: T >= 0
 makespan_vertex_11: T - 5 column_1 - 5 column_66 - 5 column_67
   - 5 column_70 - 5 column_106 - 5 column_108 - 5 column_111
   - 5 column_3286 - 5 column_3287 - 5 column_3288 - 5 column_3289
   - 5 column_3292 - 5 column_3295 - 5 column_3315 - 5 column_3325
   - 5 column_3335 >= 0
 makespan_vertex_12: T - 9 column_3294 >= 0
 makespan_vertex_13: T - 2 column_4 >= 0
 makespan_vertex_14: T - 10 column_107 - 10 column_3290 - 10 column_3291
   - 10 column_3293 >= 0
 makespan_vertex_15: T - 6 column_2 - 6 column_77 - 6 column_106
   - 6 column_107 - 6 column_108 - 6 column_111 - 6 column_3306
   - 6 column_3307 - 6 column_3308 - 6 column_3309 - 6 column_3310
   - 6 column_3311 - 6 column_3312 - 6 column_3313 - 6 column_3314
   - 6 column_3315 >= 0
 makespan_vertex_16: T - column_4 >= 0
 makespan_vertex_17: T >= 0
 makespan_vertex_18: T - 7 column_1 - 7 column_95 - 7 column_106
   - 7 column_107 - 7 column_108 - 7 column_111 - 7 column_3286
   - 7 column_3287 - 7 column_3288 - 7 column_3289 - 7 column_3290
   - 7 column_3291 - 7 column_3292 - 7 column_3293 - 7 column_3294
   - 7 column_3295 - 7 column_3326 - 7 column_3327 - 7 column_3328
   - 7 column_3329 - 7 column_3330 - 7 column_3331 - 7 column_3332
   - 7 column_3333 - 7 column_3334 - 7 column_3335 >= 0
 makespan_vertex_19: T - 4 column_4 >= 0
 makespan_vertex_20: T - 8 column_2 >= 0
 makespan_vertex_21: T - 9 column_36 - 9 column_40 - 9 column_3306
   - 9 column_3307 - 9 column_3308 - 9 column_3309 - 9 column_3310
   - 9 column_3311 - 9 column_3312 - 9 column_3313 - 9 column_3314
   - 9 column_3315 - 9 column_3326 - 9 column_3327 - 9 column_3328
   - 9 column_3329 - 9 column_3330 - 9 column_3331 - 9 column_3332
   - 9 column_3333 - 9 column_3334 - 9 column_3335 >= 0
 makespan_vertex_22: T - 9 column_1 >= 0
 makespan_vertex_23: T - column_5 - column_66 - column_67 - column_70
   - column_77 - column_95 - column_106 - column_107 - column_108
   - column_111 - column_3307 - column_3308 - column_3310 - column_3312
   - column_3314 - column_3315 - column_3316 - column_3318 - column_3320
   - column_3322 - column_3324 - column_3325 - column_3327 - column_3328
   - column_3330 - column_3332 - column_3334 - column_3335 >= 0
 makespan_vertex_24: T >= 0
 makespan_vertex_25: T >= 0
 makespan_vertex_26: T - 10 column_2 >= 0
 makespan_vertex_27: T >= 0
 makespan_vertex_28: T >= 0
 makespan_vertex_29: T - 9 column_77 - 9 column_106 - 9 column_107
   - 9 column_108 - 9 column_111 - 9 column_3316 - 9 column_3317
   - 9 column_3318 - 9 column_3319 - 9 column_3320 - 9 column_3321
   - 9 column_3322 - 9 column_3323 - 9 column_3324 - 9 column_3325 >= 0
 charger_capacity_constraint: column_1 + column_2 + column_4 + column_5
   + column_36 + column_40 + column_66 + column_67 + column_70 + column_77
   + column_95 + column_106 + column_107 + column_108 + column_111
   + column_3286 + column_3287 + column_3288 + column_3289 + column_3290
   + column_3291 + column_3292 + column_3293 + column_3294 + column_3295
   + column_3306 + column_3307 + column_3308 + column_3309 + column_3310
   + column_3311 + column_3312 + column_3313 + column_3314 + column_3315
   + column_3316 + column_3317 + column_3318 + column_3319 + column_3320
   + column_3321 + column_3322 + column_3323 + column_3324 + column_3325
   + column_3326 + column_3327 + column_3328 + column_3329 + column_3330
   + column_3331 + column_3332 + column_3333 + column_3334 + column_3335
   <= 2
Bounds
End
