# Parser implementation for MALI language.

import ply.yacc as yacc
from implementation.scanner import tokens
import implementation.semantic_and_quadruples as sq
from implementation.utils.parser_utils import *  # pylint: disable=unused-wildcard-import
from implementation.utils.constants import Types, func_types, Operations, str_operations, Access, str_access
import json

import pprint
pp = pprint.PrettyPrinter()
pprint.sorted = lambda x, key=None: x

input_str = ''
error = False

# Syntax rules.


def p_program(p):
  '''program : classes vars modules main
             | classes vars main
             | classes modules main
             | modules main
             | vars modules main
             | classes main
             | vars main
             | main'''
  add_to_tree('program', p)


def p_classes(p):
  '''classes : class classes
             | class'''
  add_to_tree('classes', p)


def p_class(p):
  '''class : CLASS ID r_seen_class classblock r_finish_class
           | CLASS ID r_seen_class EXTENDS ID r_class_parent classblock \
             r_finish_class'''
  add_to_tree('class', p)


def p_classblock(p):
  '''classblock : LEFT_B attributes init methods RIGHT_B
                | LEFT_B init methods RIGHT_B
                | LEFT_B attributes init RIGHT_B
                | LEFT_B init RIGHT_B'''
  add_to_tree('classblock', p)


def p_attributes(p):
  '''attributes : ATTR LEFT_B attr_dec RIGHT_B'''
  add_to_tree('attributes', p)


def p_attr_dec(p):
  '''attr_dec : access var attr_dec
              | access var'''
  add_to_tree('attr_dec', p)


def p_init(p):
  '''init : INIT r_seen_init LEFT_P param RIGHT_P init_factor r_finish_func'''
  add_to_tree('init', p)


def p_init_factor(p):
  '''init_factor : r_start_func proc_block
                 | COLON r_start_func ID r_call_parent param_pass \
                   r_finish_parent_call proc_block '''
  add_to_tree('init_factor', p)


def p_methods(p):
  '''methods : access proc r_set_access methods
             | access proc r_set_access'''
  add_to_tree('methods', p)


def p_access(p):
  '''access : PUBLIC r_seen_access
            | PRIVATE r_seen_access
            | PROTECTED r_seen_access'''
  add_to_tree('access', p)


def p_vars(p):
  '''vars : VAR LEFT_B vars_dec RIGHT_B'''
  add_to_tree('vars', p)


def p_vars_dec(p):
  '''vars_dec : var vars_dec
              | var'''
  add_to_tree('vars_dec', p)


def p_var(p):
  '''var : complex_type var_aux SC'''
  add_to_tree('var', p)


def p_var_aux(p):
  '''var_aux : ID r_var_name COMMA var_aux
             | ID r_var_name
             | ID r_var_name arr_dim COMMA var_aux
             | ID r_var_name arr_dim'''
  add_to_tree('var_aux', p)


def p_arr_dim(p):
  '''arr_dim : LEFT_SB CTE_I RIGHT_SB
             | LEFT_SB CTE_I RIGHT_SB LEFT_SB CTE_I RIGHT_SB'''


def p_type(p):
  '''type : INT r_seen_type
          | FLOAT r_seen_type
          | CHAR r_seen_type
          | BOOL r_seen_type'''
  add_to_tree('type', p)


def p_complex_type(p):
  '''complex_type : type
                  | ID r_seen_type'''


def p_modules(p):
  '''modules : FUNCTION proc modules
             | FUNCTION proc'''
  add_to_tree('modules', p)


def p_proc(p):
  '''proc : type ID r_funcName LEFT_P param RIGHT_P r_start_func proc_block \
            r_finish_func
          | VOID r_seen_type ID r_funcName LEFT_P param RIGHT_P r_start_func \
            proc_block r_finish_func'''
  add_to_tree('proc', p)


def p_proc_block(p):
  '''proc_block : LEFT_B vars statements RIGHT_B
                | LEFT_B vars RIGHT_B
                | block'''
  add_to_tree('proc_block', p)


def p_param(p):
  '''param : r_seen_param params r_finish_param
           | r_seen_param r_finish_param'''
  add_to_tree('param', p)


def p_params(p):
  '''params : complex_type ID r_var_name COMMA params
            | complex_type ID r_var_name
            | complex_type ID r_var_name arr_index COMMA params
            | complex_type ID r_var_name arr_index'''
  add_to_tree('params', p)


def p_statements(p):
  '''statements : statement SC statements
                | statement SC'''
  add_to_tree('statements', p)


def p_statement(p):
  '''statement : assign
               | call
               | return
               | write
               | if
               | while'''
  add_to_tree('statement', p)


def p_assign(p):
  '''assign : ID r_seen_assigning_operand EQUAL expression
            | arraccess EQUAL expression
            | ID r_seen_assigning_operand EQUAL READ r_do_read
            | arraccess EQUAL READ r_do_read'''
  e = sq.do_assign()
  if e:
    handle_error(p.lineno(1), p.lexpos(1), e)
  add_to_tree('assign', p)


def p_call(p):
  '''call : path'''
  sq.finish_call()
  add_to_tree('call', p)


def p_path(p):
  '''path : ID r_switch_instance DOT path_aux
          | ID r_start_local_func_call param_pass'''
  add_to_tree('path', p)


def p_path_aux(p):
  '''path_aux : ID r_switch_instance DOT path_aux
              | ID r_start_instance_func_call param_pass
              | INIT r_start_init_call param_pass
              | ID r_attribute_call'''
  add_to_tree('path_aux', p)


def p_param_pass(p):
  '''param_pass : LEFT_P r_start_params RIGHT_P r_done_param_pass
                | LEFT_P r_start_params param_pass_aux RIGHT_P r_done_param_pass'''
  add_to_tree('param_pass', p)


def p_r_push_fake_bottom(p):
  'r_push_fake_bottom : '
  sq.register_operator(Operations.FAKE_BOTTOM)


def p_param_pass_aux(p):
  '''param_pass_aux : r_push_fake_bottom expression r_pass_param \
                      r_pop_fake_bottom COMMA r_next_param_pass param_pass_aux
                    | r_push_fake_bottom expression r_pass_param \
                      r_pop_fake_bottom'''
  add_to_tree('param_pass_aux', p)


def p_return(p):
  '''return : RETURN expression r_seen_return'''
  add_to_tree('return', p)


def p_write(p):
  '''write : WRITE words'''
  add_to_tree('write', p)


def p_words(p):
  '''words : CTE_STR r_do_write_str COMMA words
           | CTE_STR r_do_write_str
           | expression r_do_write COMMA words
           | expression r_do_write'''
  add_to_tree('words', p)


def p_if(p):
  '''if : IF condition'''
  add_to_tree('if', p)


def p_condition(p):
  '''condition : LEFT_P expression RIGHT_P r_seen_cond block ELIF \
                 r_seen_else condition r_seen_end_if
               | LEFT_P expression RIGHT_P r_seen_cond block ELSE \
                 r_seen_else block r_seen_end_if
               | LEFT_P expression RIGHT_P r_seen_cond block r_seen_end_if'''
  add_to_tree('condition', p)


def p_while(p):
  '''while : WHILE r_seen_while LEFT_P expression RIGHT_P r_seen_cond block \
             r_seen_end_while'''
  add_to_tree('while', p)


def p_arraccess(p):
  '''arraccess : ID arr_index'''
  add_to_tree('arraccess', p)


def p_arr_index(p):
  '''arr_index : LEFT_SB expression RIGHT_SB
               | LEFT_SB expression RIGHT_SB LEFT_SB expression RIGHT_SB'''
  add_to_tree('arr_index', p)


def p_block(p):
  '''block : LEFT_B statements RIGHT_B
           | LEFT_B RIGHT_B'''
  add_to_tree('block', p)


def p_main(p):
  '''main : MAIN r_seen_main proc_block r_finish_main'''
  add_to_tree('main', p)


def p_expression(p):
  '''expression : exp r_seen_exp AND r_seen_operator expression
                | exp r_seen_exp'''
  add_to_tree('expression', p)


def p_exp(p):
  '''exp : xp r_seen_xp OR r_seen_operator exp
         | xp r_seen_xp'''
  add_to_tree('exp', p)


def p_xp(p):
  '''xp : x r_seen_x MORE_T r_seen_operator xp
        | x r_seen_x LESS_T r_seen_operator xp
        | x r_seen_x DIFFERENT r_seen_operator xp
        | x r_seen_x ISEQUAL r_seen_operator xp
        | x r_seen_x LESS_ET r_seen_operator xp
        | x r_seen_x MORE_ET r_seen_operator xp
        | x r_seen_x'''
  add_to_tree('xp', p)


def p_x(p):
  '''x : term r_seen_term PLUS r_seen_operator x
       | term r_seen_term MINUS r_seen_operator x
       | term r_seen_term'''
  add_to_tree('x', p)


def p_term(p):
  '''term : factor r_seen_factor TIMES r_seen_operator term
          | factor r_seen_factor DIV r_seen_operator term
          | factor r_seen_factor'''
  add_to_tree('term', p)


def p_factor(p):
  '''factor : not LEFT_P r_seen_operator expression RIGHT_P r_pop_fake_bottom
            | not sign cte'''
  add_to_tree('factor', p)


def p_not(p):
  '''not : NOT
         | empty'''
  add_to_tree('not', p)


def p_sign(p):
  '''sign : PLUS
         | MINUS
         | empty'''
  add_to_tree('sign', p)


def p_cte(p):
  '''cte : ID r_seen_operand
         | CTE_I r_seen_operand
         | CTE_F r_seen_operand
         | CTE_CH r_seen_operand
         | arraccess
         | call'''
  add_to_tree('cte', p)


# Rule used to create an cfg epsilon-like value.
def p_empty(p):
  '''empty :'''
  add_to_tree('empty', p)


# Semantic rules.

def p_r_seen_class(p):
  'r_seen_class : '
  e = sq.seen_class(class_name=p[-1])
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_class_parent(p):
  'r_class_parent : '
  e = sq.class_parent(class_parent=p[-1])
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_finish_class(p):
  'r_finish_class : '
  sq.finish_class()


def p_r_seen_access(p):
  'r_seen_access : '
  sq.seen_access(new_access=str_access[p[-1]])


def p_r_seen_type(p):
  'r_seen_type : '
  if p[-1].upper() in Types.__members__:
    new_type = Types[p[-1].upper()]
  else:
    new_type = p[-1]
  e = sq.seen_type(new_type=new_type)
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_var_name(p):
  'r_var_name : '
  e = sq.var_name(var_name=p[-1])
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_seen_init(p):
  'r_seen_init : '
  sq.set_current_type_void()
  e = sq.seen_func(func_name='init')
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_seen_param(p):
  'r_seen_param : '
  sq.switch_param(True)


def p_r_finish_param(p):
  'r_finish_param : '
  sq.switch_param(False)


def p_r_call_parent(p):
  'r_call_parent : '
  e = sq.call_parent(parent=p[-1])
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_finish_parent_call(p):
  'r_finish_parent_call : '
  sq.finish_parent_call()


def p_r_funcName(p):
  'r_funcName : '
  e = sq.seen_func(func_name=p[-1])
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_set_access(p):
  'r_set_access : '
  sq.set_access()


def p_r_seen_main(p):
  'r_seen_main : '
  sq.register_main_beginning()
  sq.set_current_type_void()
  e = sq.seen_func(func_name='#main')
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_seen_operand(p):
  'r_seen_operand : '
  e = sq.register_operand(p[-1])
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)

def p_r_seen_assigning_operand(p):
  'r_seen_assigning_operand : '
  e = sq.register_operand(p[-1], mark_assigned=True)
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_seen_operator(p):
  'r_seen_operator : '
  sq.register_operator(str_operations[p[-1]])


def p_r_seen_factor(p):
  'r_seen_factor : '
  sq.solve_operation_or_continue([Operations.TIMES, Operations.DIV])


def p_r_seen_term(p):
  'r_seen_term : '
  sq.solve_operation_or_continue([Operations.PLUS, Operations.MINUS])


def p_r_seenX(p):
  'r_seen_x : '
  sq.solve_operation_or_continue(
      [Operations.MORE_THAN, Operations.LESS_THAN, Operations.DIFFERENT,
       Operations.IS_EQUAL, Operations.LESS_EQUAL, Operations.MORE_EQUAL])


def p_r_seen_xp(p):
  'r_seen_xp : '
  sq.solve_operation_or_continue([Operations.OR])


def p_r_seen_exp(p):
  'r_seen_exp : '
  sq.solve_operation_or_continue([Operations.AND])


def p_r_pop_fake_bottom(p):
  'r_pop_fake_bottom : '
  sq.pop_fake_bottom()


def p_r_do_write_str(p):
  'r_do_write_str : '
  sq.do_write(p[-1])


def p_r_do_write(p):
  'r_do_write : '
  e = sq.do_write()
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_do_read(p):
  'r_do_read : '
  sq.do_read()


def p_r_seen_cond(p):
  'r_seen_cond : '
  e = sq.register_condition()
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_seen_else(p):
  'r_seen_else : '
  sq.register_else()


def p_r_seen_end_if(p):
  'r_seen_end_if : '
  sq.register_end_if()


def p_r_seen_while(p):
  'r_seen_while : '
  sq.register_while()


def p_r_seen_end_while(p):
  'r_seen_end_while : '
  sq.register_end_while()


def p_r_start_func(p):
  'r_start_func : '
  sq.register_function_beginning()


def p_r_finish_func(p):
  'r_finish_func : '
  e = sq.register_func_end()
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_finish_main(p):
  'r_finish_main : '
  e = sq.register_func_end(is_main=True)
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_seen_return(p):
  'r_seen_return : '
  sq.register_return()


def p_r_start_local_func_call(p):
  'r_start_local_func_call : '
  e = sq.start_func_call(p[-1])
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_start_instance_func_call(p):
  'r_start_instance_func_call : '
  e = sq.start_instance_func_call(p[-1])
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_start_init_call(p):
  'r_start_init_call : '
  e = sq.start_instance_func_call(p[-1], is_init=True)
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_attribute_call(p):
  'r_attribute_call : '
  e = sq.instance_attribute_call(p[-1])
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_start_params(p):
  'r_start_params : '
  sq.start_param_collection()


def p_r_pass_param(p):
  'r_pass_param : '
  e = sq.pass_param()
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_next_param_pass(p):
  'r_next_param_pass : '
  e = sq.prepare_upcoming_param()
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_done_param_pass(p):
  'r_done_param_pass : '
  e = sq.done_param_pass()
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


def p_r_switch_instance(p):
  'r_switch_instance : '
  e = sq.switch_instance(p[-1])
  if e:
    handle_error(p.lineno(-1), p.lexpos(-1), e)


# Syntax error detection rules.

def p_e_program_missing_main(p):
  '''program : classes vars modules
             | classes modules
             | modules
             | vars modules
             | classes
             | vars'''
  handle_error(input_str.count('\n'), input_str.rfind('\n'),
               'Missing main block.')


def p_e_program_main_not_end(p):
  '''program : classes vars modules main error
             | classes modules main error
             | modules main error
             | vars modules main error
             | classes main error
             | vars main error
             | main error'''
  pos = len(p)-1
  handle_error(p.lineno(pos), p.lexpos(pos),
               'The code should end with the main block.')


def p_e_program_disorder(p):
  '''program : vars classes error
             | modules classes error
             | vars modules classes error
             | modules vars error'''
  handle_error(0, 0, 'Bad program structure, should be: classes -> ' +
               'global vars -> modules -> main')


# Syntax error printing.

def handle_error(line, lexpos, mssg):
  global error
  error = True
  error_prefix(line, lexpos, input_str)
  print(mssg)
  recover_parser(parser)


def p_error(p):
  global error
  error = True
  error_prefix(p.lineno, p.lexpos, input_str)
  print(f'Unexpected token {p.value}.')


# Generate parser.
parser = yacc.yacc(start='program')
parser.defaulted_states = {}


# Run parser and generate output.

def parse_string(s):
  global input_str
  input_str = s
  parser.parse(s, tracking=True)


def generate_output():
  if not error:
    pp.pprint(sq.classes)
    q_count = 0
    for q, vq in zip(sq.quadruples, sq.visual_quadruples):
      print('{0:<5} {1:<40} {2:<40}'.format(
          str(q_count) + ':', str(q), str(vq)))
      q_count += 1

  if error:
    return
  output = sq.generate_output()
  # pp.pprint(output)
  # out = eval(str(output))
  return str(output)
