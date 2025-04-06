proc @fib(%n):
%.L0:
  %1 = const 0;
  %2 = sub %n, %1;
  jz %2, %.L6;
  jmp %.L1;
%.L1:
  %3 = const 1;
  %4 = sub %n, %3;
  jz %4, %.L4;
  jmp %.L2;
%.L2:
  %5 = const 1;
  %6 = sub %n, %5;
  param 1, %6;
  %7 = call @fib, 1;
  %8 = const 2;
  %9 = sub %n, %8;
  param 1, %9;
  %10 = call @fib, 1;
  %11 = add %7, %10;
  %0 = copy %11;
  jmp %.L7;
%.L3:
  jmp %.L5;
%.L4:
  %12 = const 1;
  %0 = copy %12;
  jmp %.L7;
%.L5:
  jmp %.L7;
%.L6:
  %13 = const 0;
  %0 = copy %13;
  jmp %.L7;
%.L7:
  ret %0;

proc @main():
%.L0:
  %0 = const 0;
  %1 = copy %0;
  jmp %.L1;
%.L1:
  %2 = const 10;
  %3 = sub %1, %2;
  jl %3, %.L2;
  jmp %.L3;
%.L2:
  param 1, %1;
  %4 = call @fib, 1;
  param 1, %4;
  call @__bx_print_int, 1;
  %5 = const 1;
  %6 = add %1, %5;
  %1 = copy %6;
  jmp %.L1;
%.L3:
  ret;
