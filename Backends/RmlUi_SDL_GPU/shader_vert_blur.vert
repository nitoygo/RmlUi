#include "shader_common.hlsli"

// The quad to draw: the two corners in clip space, then the texture coordinate at the first corner
// followed by the span across the quad. Both are per-pass, which is why they are constants and not
// vertex data -- see DrawPostprocessQuad() in the renderer.
cbuffer UniformBlockBlur : register(b0, space1) {
    float4 QuadPosition : packoffset(c0);
    float4 QuadTexCoord : packoffset(c1);
    float2 TexelOffset : packoffset(c2);
};

// The taps the fragment stage takes are spaced evenly along a row, so this stage hands over the coordinate at the
// quad's vertex and the step between taps, and the fragment stage works out each tap. The quad itself comes from the
// constant buffer, as in the passthrough stage.
BlurVertexOutput main(VertexInput input) {
    BlurVertexOutput output;
    output.TexCoord = QuadTexCoord.xy + input.TexCoord * QuadTexCoord.zw;
    output.TexelOffset = TexelOffset;
    output.Position = float4(lerp(QuadPosition.xy, QuadPosition.zw, input.TexCoord), 0, 1);
    return output;
}
