"""Enhancement for the Pdb built-in debugger
"""
import pdb


class Pdb(pdb.Pdb):
    NON_USER_PATHS = [
        pdb.__file__.rsplit("/", 1)[0] + "/"
    ]

    def do_up_user(self, arg):
        """uu / up_user
        Move the current frame up until the next user code frame.
        """
        user_frames = [
            i for i, frame_lineno in enumerate(self.stack)
            if not any(frame_lineno[0].f_code.co_filename.startswith(p) for p in self.NON_USER_PATHS)
        ]
        if not user_frames:
            self.error('No user frames at all')
            return
        if min(user_frames) > self.curindex:
            self.error('Already above the highest user frame')
            return
        if min(user_frames) == self.curindex:
            self.error('Already at the top user frame')
            return
        new_frame = max(i for i in user_frames if i < self.curindex)
        self.message(f'u {self.curindex - new_frame}')
        self._select_frame(new_frame)
    do_uu = do_up_user


def install_as_default():
    pdb.Pdb = Pdb
