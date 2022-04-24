from vim_turing_machine.machines.weird_calc.encode_input_str import encode_input_str
from vim_turing_machine.vim_machine import VimTuringMachine
from vim_turing_machine.constants import BLANK_CHARACTER
from vim_turing_machine.constants import INITIAL_STATE
from vim_turing_machine.constants import VALID_CHARACTERS
from vim_turing_machine.constants import YES_FINAL_STATE
from vim_turing_machine.struct import BACKWARDS
from vim_turing_machine.struct import DO_NOT_MOVE
from vim_turing_machine.struct import FORWARDS
from vim_turing_machine.struct import StateTransition
from vim_turing_machine.turing_machine import TuringMachine

import itertools

class weird_calc_generator:
	def __init__(self, num_bits, initial_tape_len):
		self._num_bits = num_bits
		self._initial_tape_len = initial_tape_len

	def gen_states_transitions(self):
		array_of_arrays_len=self._initial_tape_len//(self._num_bits*4)
		def state_name(array_idx):
			if(array_idx == 0):
				return INITIAL_STATE
			elif(array_idx == array_of_arrays_len):
				return YES_FINAL_STATE
			return '{}Idx{}'.format(INITIAL_STATE,array_idx)

		base_encrypt_stage1="{}Stage1"
		base_encrypt_stage2="{}Stage2"
		base_encrypt_stage3="{}Stage3"

		transitions=[]
		for array_idx in range(array_of_arrays_len):
			transitions.extend((
				*self.copy_bits_to_end_of_buffer(
					initial_state=state_name(array_idx),
					num_bits=self._num_bits*4,
					final_state=base_encrypt_stage1.format(state_name(array_idx))
				),
				*self.left_shift_n(
					initial_state=base_encrypt_stage1.format(state_name(array_idx)),
					shift_bits=5,
					final_state=base_encrypt_stage2.format(state_name(array_idx))
				),
				*self.xor(
					initial_state=base_encrypt_stage2.format(state_name(array_idx)),
					num_bits=self._num_bits*4,
					step_bits=self._num_bits*4*(array_of_arrays_len-array_idx)+1,
					direction=BACKWARDS,
					final_state=state_name(array_idx+1),
				)
			))
		return transitions
	
	def left_shift_n(self,initial_state,shift_bits,final_state):
		'''
		Precondition: We are at the end of the buffer
        Postcondition: We are at the end of the buffer
		'''
		def state_name(shift_idx):
			if(shift_idx==shift_bits):
				return final_state
			return '{}times{}'.format(initial_state,shift_idx)

		base_reset_to_right="{}CursorReset"
		#set the cursor to the end of buffer
		transitions=self.move_to_blank_spaces(
						initial_state=initial_state,
						final_state=state_name(0),
                		final_character=BLANK_CHARACTER,
                		final_direction=BACKWARDS,
                		direction=FORWARDS,
                		num_blanks=1,
					)
		for shift_idx in range(shift_bits):
			transitions.extend((
				*self.left_shift(
					initial_state=state_name(shift_idx),
					num_bits=self._num_bits*4,
					final_state=base_reset_to_right.format(state_name(shift_idx)),
				),
				*self.move_to_blank_spaces(
					initial_state=base_reset_to_right.format(state_name(shift_idx)),
					final_state=state_name(shift_idx+1),
                	final_character=BLANK_CHARACTER,
                	final_direction=BACKWARDS,
                	direction=FORWARDS,
                	num_blanks=1,
				)
			))
		return transitions
	
	def left_shift(self,initial_state,num_bits,final_state):
		'''
		Precondition: We are at the end of the src
        Postcondition: We are at the start of the src
		'''
		def state_name(bit_idx):
			return '{}Unknown{}'.format(initial_state, bit_idx)
		
		def shift_bit(bit_idx):
			pre_0_state = '{}Bit0'.format(state_name(bit_idx))
			post_0_state = '{}Bit0'.format(state_name(bit_idx + 1)) if bit_idx<num_bits-2 else final_state
			pre_1_state = '{}Bit1'.format(state_name(bit_idx))
			post_1_state = '{}Bit1'.format(state_name(bit_idx + 1)) if bit_idx<num_bits-2 else final_state
			direction = BACKWARDS if bit_idx<num_bits-2 else DO_NOT_MOVE
			
			return [
				StateTransition(
					previous_state=pre_0_state,
					previous_character='0',
					next_state=post_0_state,
					next_character='0',
					tape_pointer_direction=direction,
				),
				StateTransition(
					previous_state=pre_0_state,
					previous_character='1',
					next_state=post_1_state,
					next_character='0',
					tape_pointer_direction=direction,
				),
				StateTransition(
					previous_state=pre_1_state,
					previous_character='0',
					next_state=post_0_state,
					next_character='1',
					tape_pointer_direction=direction,
				),
				StateTransition(
					previous_state=pre_1_state,
					previous_character='1',
					next_state=post_1_state,
					next_character='1',
					tape_pointer_direction=direction
				)
			]
		
		transitions=list((
			StateTransition(
				previous_state=initial_state,
				previous_character='0',
				next_state='{}Bit0'.format(state_name(0)),
				next_character='0',
				tape_pointer_direction=BACKWARDS,
			),
			StateTransition(
				previous_state=initial_state,
				previous_character='1',
				next_state='{}Bit1'.format(state_name(0)),
				next_character='0',
				tape_pointer_direction=BACKWARDS,
			))
		)
		for bit_idx in range(num_bits-1):
			transitions.extend(shift_bit(bit_idx))
		
		return transitions

	def xor(self,initial_state,num_bits,step_bits,direction,final_state):
		'''
		step_bits: dst_pos-src_pos
		Precondition: We are at the end of the src array
        Postcondition: We are at the rear of the end of the dst array and the src array is clear
		'''
		def state_name(bit_idx,bit_val=None):
			if(bit_val):
				return '{}Guess{}Bit{}'.format(initial_state, bit_idx, bit_val)
			if(bit_idx == 0):
				return initial_state
			elif(bit_idx == num_bits):
				return final_state
			return '{}Guess{}'.format(initial_state, bit_idx)
		
		if(not step_bits):
			assert(direction==DO_NOT_MOVE)
		else:
			assert(direction!=DO_NOT_MOVE)
		
		base_stepping_state="{}Step"
		base_stepping_back_state="{}StepBack"
		base_end_stepping_state="{}StepEnd"
		transitions=[]
		for bit_idx in range(num_bits):
			transitions.extend((
				StateTransition(
					previous_character='0',
					previous_state=state_name(bit_idx),
					next_state=base_stepping_state.format(state_name(bit_idx,0)),
					next_character=BLANK_CHARACTER,
					tape_pointer_direction=DO_NOT_MOVE,
				),
				StateTransition(
					previous_character='1',
					previous_state=state_name(bit_idx),
					next_state=base_stepping_state.format(state_name(bit_idx,1)),
					next_character=BLANK_CHARACTER,
					tape_pointer_direction=DO_NOT_MOVE,
				),
				*self.step(
					initial_state=base_stepping_state.format(state_name(bit_idx,0)),
					step_bits=step_bits,
					direction=direction,
					final_state=base_end_stepping_state.format(state_name(bit_idx,0))
				),
				*self.step(
					initial_state=base_stepping_state.format(state_name(bit_idx,1)),
					step_bits=step_bits,
					direction=direction,
					final_state=base_end_stepping_state.format(state_name(bit_idx,1))
				),
				StateTransition(
					previous_state=base_end_stepping_state.format(state_name(bit_idx,0)),
					previous_character='0',
					next_state=base_stepping_back_state.format(state_name(bit_idx+1)),
					next_character='0',
					tape_pointer_direction=DO_NOT_MOVE,
				),
				StateTransition(
					previous_state=base_end_stepping_state.format(state_name(bit_idx,0)),
					previous_character='1',
					next_state=base_stepping_back_state.format(state_name(bit_idx+1)),
					next_character='1',
					tape_pointer_direction=DO_NOT_MOVE,
				),
				StateTransition(
					previous_state=base_end_stepping_state.format(state_name(bit_idx,1)),
					previous_character='0',
					next_state=base_stepping_back_state.format(state_name(bit_idx+1)),
					next_character='1',
					tape_pointer_direction=DO_NOT_MOVE,
				),
				StateTransition(
					previous_state=base_end_stepping_state.format(state_name(bit_idx,1)),
					previous_character='1',
					next_state=base_stepping_back_state.format(state_name(bit_idx+1)),
					next_character='0',
					tape_pointer_direction=DO_NOT_MOVE,
				),
				*self.step(
					initial_state=base_stepping_back_state.format(state_name(bit_idx+1)),
					step_bits=step_bits-1 if bit_idx<num_bits-1 else num_bits,
					direction=-direction,
					final_state=state_name(bit_idx+1)
				)
			))
		return transitions

	def step(self,initial_state,step_bits,direction,final_state):

		def state_name(step_idx):
			if(step_idx == 0):
				return initial_state
			elif(step_idx==step_bits):
				return final_state
			if(direction==FORWARDS):
				return '{}Forward{}'.format(initial_state, step_idx)
			else:
				return '{}Backward{}'.format(initial_state, step_idx)

		transitions=[]
		for step_idx in range(step_bits):
			transitions.extend((
				StateTransition(
					previous_state=state_name(step_idx),
					previous_character='0',
					next_state=state_name(step_idx+1),
					next_character='0',
					tape_pointer_direction=direction,
				),
				StateTransition(
					previous_state=state_name(step_idx),
					previous_character='1',
					next_state=state_name(step_idx+1),
					next_character='1',
					tape_pointer_direction=direction,
				),
				StateTransition(
					previous_state=state_name(step_idx),
					previous_character=BLANK_CHARACTER,
					next_state=state_name(step_idx+1),
					next_character=BLANK_CHARACTER,
					tape_pointer_direction=direction,
				)
			))

		return transitions

	def copy_bits_to_end_of_buffer(self, initial_state, num_bits, final_state):
		
		def state_name(bit_idx):
			if(bit_idx == 0):
				return initial_state
			else:
				return '{}Copy{}'.format(initial_state, bit_idx)

		def copy_bit(bit_idx, bit_value):
			base_copying_state = '{}Bit{}'.format(state_name(bit_idx + 1), bit_value)

			return [
				# Let's start copying the character. Note how we replace it with a blank.
				StateTransition(
					previous_state=state_name(bit_idx),
					previous_character=bit_value,
					next_state='{}Forward'.format(base_copying_state),
					next_character=BLANK_CHARACTER if bit_idx < num_bits - 1 else bit_value,
					tape_pointer_direction=FORWARDS,
				),

				*self.move_to_blank_spaces(
					initial_state='{}Forward'.format(base_copying_state),
					# If we're on the last character, don't go backwards
					final_state=(
						'{}Backwards'.format(base_copying_state)
						if bit_idx < num_bits - 1
						else final_state
					),
					final_character=bit_value,
					final_direction=DO_NOT_MOVE,
					direction=FORWARDS,
					num_blanks=2,
				),
				*self.move_to_blank_spaces(
					initial_state='{}Backwards'.format(base_copying_state),
					final_state=state_name(bit_idx + 1),
					final_character=bit_value,
					final_direction=FORWARDS,
					direction=BACKWARDS,
					num_blanks=2,
				),
			]

		return itertools.chain.from_iterable(
			(
				*copy_bit(bit_idx, bit_value='0'),
				*copy_bit(bit_idx, bit_value='1'),
			)
			for bit_idx in range(num_bits)
		)
	
	def move_to_blank_spaces(
		self,
		initial_state,
		final_state,
		final_character,
		final_direction,
		direction,
		num_blanks,
	):

		def state_name(blank_num):
			return '{}Searching{}'.format(initial_state, blank_num)

		transitions = [
			# Rename our current state
			StateTransition(
				previous_state=initial_state,
				previous_character=character,
				next_state=state_name(blank_num=0),
				next_character=character,
				tape_pointer_direction=DO_NOT_MOVE,
			)
			for character in VALID_CHARACTERS
		]

		for blank_num in range(num_blanks):
			transitions.extend(
				# If we're looking for the first blank, then keep going until we hit it
				self.noop_when_non_blank(state_name(blank_num=blank_num), direction=direction)
			)

			if blank_num == num_blanks - 1:
				# This is the last blank
				transitions.append(
					StateTransition(
						previous_state=state_name(blank_num),
						previous_character=BLANK_CHARACTER,
						next_state=final_state,
						next_character=final_character,
						tape_pointer_direction=final_direction,
					)
				)
			else:
				# This is not the last blank
				transitions.append(
					StateTransition(
						previous_state=state_name(blank_num),
						previous_character=BLANK_CHARACTER,
						next_state=state_name(blank_num + 1),
						next_character=BLANK_CHARACTER,
						tape_pointer_direction=direction,
					)
				)
		return transitions
	
	def noop_when_non_blank(self, state, direction):
		return (
			StateTransition(
				previous_state=state,
				previous_character='0',
				next_state=state,
				next_character='0',
				tape_pointer_direction=direction,
			),
			StateTransition(
				previous_state=state,
				previous_character='1',
				next_state=state,
				next_character='1',
				tape_pointer_direction=direction,
			),
		)


def main():
	flag = "TeX7_1s_Ex3cu7@bl3"
	if(len(flag)&3): # padding
		flag+=(4-len(flag)&3)*'*'
	num_bits=8
	initial_tape = encode_input_str(flag, num_bits)
	generator = weird_calc_generator(num_bits,num_bits*len(flag))
	weird_calc_machine = VimTuringMachine(generator.gen_states_transitions(), debug=False)
	weird_calc_machine.run(initial_tape=initial_tape)

if __name__ == '__main__':
	main()