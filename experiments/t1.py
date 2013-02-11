class O(object):

    def __del__(self):
        print '__del__()'


o = O()
