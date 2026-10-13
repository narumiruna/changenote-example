/// Return the example package greeting.
pub fn hello() -> &'static str {
    "Hello from pkg-rust!"
}

#[cfg(test)]
mod tests {
    use super::hello;

    #[test]
    fn hello_returns_a_greeting() {
        assert_eq!(hello(), "Hello from pkg-rust!");
    }
}
