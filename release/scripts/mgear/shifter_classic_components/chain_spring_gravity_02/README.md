FK chain with spring and gravity, based on `chain_spring_gravity_01`
(Emilio Serrano contribution).

New in this version:

* **Stackable**: drives `chain_stack_01`, `lite_chain_stack_01/02` and other
  `chain_spring_gravity_02` chains as master, and follows a master chain as
  slave (Master Local / Master Global, Connection Offset, Local and World
  Blend). The spring is added on top of the master motion.
* **Scalable**: the rig holds under global scale. The spring and gravity
  values are in world units and don't change with the scale.
* **Extra Tweak**: one tweak control per segment, after the spring, driving
  the joint.
* **Tweak End**: a control and a joint at the chain tip.

The Mirror Behaviour L and R option of v01 is kept.
