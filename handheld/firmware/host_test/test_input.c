#include <assert.h>
#include <stdio.h>
#include "../main/struthio_input.h"

static void sample_range(struthio_input_mapper_t *m, unsigned a, unsigned b, bool l, bool r, bool boot)
{
    for (unsigned t=a; t<=b; ++t) struthio_input_sample(m,l,r,t,boot);
}

int main(void)
{
    struthio_input_mapper_t m;
    struthio_input_frame_t f;

    // 1) left press -> immediate debounced left flap
    struthio_input_init(&m,0);
    sample_range(&m,0,10,true,false,false);
    f=struthio_input_consume_frame(&m);
    assert(f.flap_edge && f.flap_kind==STRUTHIO_FLAP_LEFT && !f.chord_edge);

    // 2) opposite wing within 100 ms -> straight/chord correction
    sample_range(&m,11,60,true,false,false);
    sample_range(&m,61,72,true,true,false);
    f=struthio_input_consume_frame(&m);
    assert(f.flap_edge && f.flap_kind==STRUTHIO_FLAP_STRAIGHT && f.chord_edge);
    assert(!f.left_held && !f.right_held);

    // release
    sample_range(&m,73,90,false,false,false);
    (void)struthio_input_consume_frame(&m);

    // 3) hold left -> one DART at ~230 ms after debounced press
    struthio_input_init(&m,1000);
    sample_range(&m,1000,1010,true,false,false);
    (void)struthio_input_consume_frame(&m); // flap
    sample_range(&m,1011,1250,true,false,false);
    f=struthio_input_consume_frame(&m);
    assert(f.dart_edge && f.dart_side==STRUTHIO_DART_LEFT);
    sample_range(&m,1251,1400,true,false,false);
    f=struthio_input_consume_frame(&m);
    assert(!f.dart_edge); // only once per hold

    // 4) service mode only after both held through guard
    struthio_input_init(&m,2000);
    sample_range(&m,2000,2700,true,true,true);
    assert(struthio_input_service_mode_requested(&m));

    puts("PASS: STRUTHIO A0 input mapper host tests");
    return 0;
}
