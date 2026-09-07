\ Model master
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  T + 1000 column_1 + 1000 column_2
Subject To
 each_partition_colored_once_constraint0: column_1 + column_39 + column_41
   + column_43 + column_79 + column_2444 + column_2446 + column_2448
   + column_2491 + column_2492 + column_2493 + column_2494 + column_2496
   + column_2497 + column_2499 >= 1
 each_partition_colored_once_constraint1: column_2 + column_43
   + column_2440 + column_2441 + column_2444 + column_2446 + column_2448
   + column_2490 + column_2491 + column_2492 + column_2493 + column_2494
   + column_2495 + column_2496 + column_2497 + column_2498 + column_2499
   >= 1
 each_partition_colored_once_constraint2: column_1 + column_10 + column_69
   + column_79 + column_2440 + column_2441 + column_2444 + column_2446
   + column_2448 + column_2493 + column_2494 + column_2495 + column_2496
   + column_2498 >= 1
 each_partition_colored_once_constraint3: column_2 + column_19 + column_69
   + column_79 + column_2490 + column_2491 + column_2492 + column_2493
   + column_2494 + column_2495 + column_2496 + column_2497 + column_2498
   + column_2499 >= 1
 each_partition_colored_once_constraint4: column_1 + column_19
   + column_2440 + column_2441 + column_2444 + column_2446 + column_2448
   + column_2497 + column_2499 >= 1
 each_partition_colored_once_constraint5: column_2 + column_10 + column_19
   + column_32 + column_33 + column_34 + column_36 + column_37 + column_39
   + column_41 + column_43 + column_2490 + column_2491 + column_2492
   + column_2493 + column_2494 + column_2495 + column_2496 + column_2497
   + column_2498 + column_2499 >= 1
 each_partition_colored_once_constraint6: column_1 + column_32 + column_33
   + column_34 + column_36 + column_37 + column_39 + column_41 + column_43
   + column_69 + column_79 + column_2440 + column_2441 + column_2444
   + column_2446 + column_2448 >= 1
 each_partition_colored_once_constraint7: column_2 + column_32 + column_33
   + column_34 + column_36 + column_37 + column_39 + column_41 + column_43
   + column_69 + column_79 + column_2490 + column_2491 + column_2492
   + column_2493 + column_2494 + column_2495 + column_2496 + column_2497
   + column_2498 + column_2499 >= 1
 each_partition_colored_once_constraint8: column_1 + column_5 + column_10
   + column_19 + column_32 + column_33 + column_34 + column_36 + column_37
   + column_39 + column_41 + column_43 + column_69 + column_79 >= 1
 each_partition_colored_once_constraint9: column_2 + column_10 + column_37
   + column_39 + column_41 + column_2440 + column_2441 + column_2444
   + column_2446 + column_2448 + column_2490 + column_2491 + column_2492
   + column_2493 + column_2494 + column_2495 + column_2496 + column_2497
   + column_2498 + column_2499 >= 1
 makespan_vertex_0: T - column_1 >= 0
 makespan_vertex_1: T - 2 column_39 - 2 column_43 - 2 column_79
   - 2 column_2444 - 2 column_2446 >= 0
 makespan_vertex_2: T - column_41 - column_2448 - column_2491 - column_2493
   - column_2494 - column_2497 >= 0
 makespan_vertex_3: T - 12 column_2492 - 12 column_2496 - 12 column_2499
   >= 0
 makespan_vertex_4: T - 2 column_2 - 2 column_2440 - 2 column_2441
   - 2 column_2448 - 2 column_2490 - 2 column_2491 - 2 column_2492
   - 2 column_2493 - 2 column_2494 - 2 column_2495 - 2 column_2496
   - 2 column_2497 - 2 column_2498 - 2 column_2499 >= 0
 makespan_vertex_5: T - 4 column_43 - 4 column_2444 >= 0
 makespan_vertex_6: T - 4 column_2446 >= 0
 makespan_vertex_7: T - 3 column_1 - 3 column_10 - 3 column_69
   - 3 column_79 - 3 column_2440 - 3 column_2441 - 3 column_2444
   - 3 column_2446 - 3 column_2448 - 3 column_2493 - 3 column_2495
   - 3 column_2496 >= 0
 makespan_vertex_8: T - 12 column_2494 - 12 column_2498 >= 0
 makespan_vertex_9: T - 4 column_2 - 4 column_19 - 4 column_69
   - 4 column_79 - 4 column_2490 - 4 column_2491 - 4 column_2492
   - 4 column_2493 - 4 column_2494 - 4 column_2495 - 4 column_2496
   - 4 column_2497 - 4 column_2498 - 4 column_2499 >= 0
 makespan_vertex_10: T >= 0
 makespan_vertex_11: T - 5 column_1 - 5 column_2440 - 5 column_2497
   - 5 column_2499 >= 0
 makespan_vertex_12: T >= 0
 makespan_vertex_13: T >= 0
 makespan_vertex_14: T - 10 column_19 - 10 column_2441 - 10 column_2444
   - 10 column_2446 - 10 column_2448 >= 0
 makespan_vertex_15: T - 6 column_2 - 6 column_10 - 6 column_19
   - 6 column_32 - 6 column_36 - 6 column_41 - 6 column_2490
   - 6 column_2491 - 6 column_2492 - 6 column_2493 - 6 column_2494
   - 6 column_2495 - 6 column_2496 - 6 column_2497 - 6 column_2498
   - 6 column_2499 >= 0
 makespan_vertex_16: T - column_33 - column_37 - column_39 - column_43
   >= 0
 makespan_vertex_17: T - column_34 >= 0
 makespan_vertex_18: T - 7 column_1 - 7 column_33 - 7 column_34
   - 7 column_36 - 7 column_37 - 7 column_39 - 7 column_41 - 7 column_43
   - 7 column_69 - 7 column_79 - 7 column_2440 - 7 column_2441
   - 7 column_2444 - 7 column_2446 - 7 column_2448 >= 0
 makespan_vertex_19: T - 4 column_32 >= 0
 makespan_vertex_20: T - 8 column_2 - 8 column_32 - 8 column_33
   - 8 column_34 - 8 column_36 - 8 column_37 - 8 column_39 - 8 column_41
   - 8 column_43 - 8 column_2490 - 8 column_2491 - 8 column_2492
   - 8 column_2493 - 8 column_2494 - 8 column_2495 - 8 column_2496
   - 8 column_2497 - 8 column_2498 - 8 column_2499 >= 0
 makespan_vertex_21: T - 9 column_69 - 9 column_79 >= 0
 makespan_vertex_22: T - 9 column_1 - 9 column_19 - 9 column_32
   - 9 column_34 - 9 column_43 >= 0
 makespan_vertex_23: T - column_5 - column_69 - column_79 >= 0
 makespan_vertex_24: T - 9 column_33 >= 0
 makespan_vertex_25: T - 4 column_10 - 4 column_36 - 4 column_37
   - 4 column_39 - 4 column_41 >= 0
 makespan_vertex_26: T - 10 column_2 >= 0
 makespan_vertex_27: T >= 0
 makespan_vertex_28: T >= 0
 makespan_vertex_29: T - 9 column_10 - 9 column_37 - 9 column_39
   - 9 column_41 - 9 column_2440 - 9 column_2441 - 9 column_2444
   - 9 column_2446 - 9 column_2448 - 9 column_2490 - 9 column_2491
   - 9 column_2492 - 9 column_2493 - 9 column_2494 - 9 column_2495
   - 9 column_2496 - 9 column_2497 - 9 column_2498 - 9 column_2499 >= 0
 charger_capacity_constraint: column_1 + column_2 + column_5 + column_10
   + column_19 + column_32 + column_33 + column_34 + column_36 + column_37
   + column_39 + column_41 + column_43 + column_69 + column_79
   + column_2440 + column_2441 + column_2444 + column_2446 + column_2448
   + column_2490 + column_2491 + column_2492 + column_2493 + column_2494
   + column_2495 + column_2496 + column_2497 + column_2498 + column_2499
   <= 2
Bounds
End
