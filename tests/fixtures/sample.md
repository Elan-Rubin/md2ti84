# Derivatives

The **derivative** of $f(x)$ is defined as:

$$f'(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}$$

## Power Rule

For $f(x) = x^n$:

$$\frac{d}{dx} x^n = n x^{n-1}$$

## Chain Rule

If $h(x) = f(g(x))$, then:

$$h'(x) = f'(g(x)) \cdot g'(x)$$

## Common Derivatives

- $\frac{d}{dx} \sin x = \cos x$
- $\frac{d}{dx} \cos x = -\sin x$
- $\frac{d}{dx} e^x = e^x$
- $\frac{d}{dx} \ln x = \frac{1}{x}$

---

# Integration

The **antiderivative** satisfies $F'(x) = f(x)$.

$$\int x^n \, dx = \frac{x^{n+1}}{n+1} + C \quad (n \neq -1)$$

## Fundamental Theorem

$$\int_a^b f(x)\,dx = F(b) - F(a)$$
